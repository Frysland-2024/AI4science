"""Differentiable cached tetragonal PXRD forward model for Week-1 gates.

The implementation deliberately keeps Pymatgen's CPU renderer as the
authoritative P0 reference.  Structure constants and a conservative reciprocal
lattice superset are prepared once, while every q-dependent crystallographic
operation is evaluated with CUDA tensors.  This makes CUDA an acceleration
layer for the same physical equations rather than a second, simplified model.
"""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
import os
from typing import Any, Mapping, Sequence

import numpy as np
from pymatgen.analysis.diffraction.xrd import ATOMIC_SCATTERING_PARAMS
from pymatgen.core import Structure


# Required by deterministic CUDA GEMM when torch deterministic algorithms are
# enabled.  Set it before importing torch.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import torch


TORCH_FORWARD_CONTRACT = "tetragonal_torch_dense_v1"


@dataclass(frozen=True)
class GPUForwardProvenance:
    contract: str
    torch_version: str
    cuda_runtime: str | None
    device: str
    device_name: str
    dtype: str
    reflection_count: int
    peak_group_count: int
    gaussian_support: str


def _axis_values(grid_config: Mapping[str, Any]) -> np.ndarray:
    minimum = float(grid_config["two_theta_min"])
    maximum = float(grid_config["two_theta_max"])
    step = float(grid_config["step"])
    count = int(round((maximum - minimum) / step)) + 1
    axis = minimum + np.arange(count, dtype=np.float64) * step
    axis[-1] = maximum
    return axis


def _element_scattering_arrays(
    structure: Structure, hkl: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Collapse fixed site phases into one sufficient statistic per element."""

    symbols = sorted({specie.symbol for site in structure for specie in site.species})
    symbol_to_index = {symbol: index for index, symbol in enumerate(symbols)}
    atomic_numbers = np.empty(len(symbols), dtype=np.float64)
    coefficients = np.empty((len(symbols), 4, 2), dtype=np.float64)
    for symbol, index in symbol_to_index.items():
        specie = next(
            specie
            for site in structure
            for specie in site.species
            if specie.symbol == symbol
        )
        atomic_numbers[index] = float(specie.Z)
        try:
            coefficients[index] = np.asarray(
                ATOMIC_SCATTERING_PARAMS[symbol], dtype=np.float64
            )
        except KeyError as error:
            raise ValueError(
                f"missing Pymatgen XRD scattering coefficients for {symbol}"
            ) from error

    phase_sum = np.zeros((len(hkl), len(symbols)), dtype=np.complex128)
    hkl_float = np.asarray(hkl, dtype=np.float64)
    for site in structure:
        phase = np.exp(
            2j
            * math.pi
            * (hkl_float @ np.asarray(site.frac_coords, dtype=np.float64))
        )
        for specie, occupancy in site.species.items():
            phase_sum[:, symbol_to_index[specie.symbol]] += float(occupancy) * phase
    return atomic_numbers, coefficients, phase_sum.real, phase_sum.imag


def _lattice_extrema(
    structure: Structure, parameter_config: Mapping[str, Any]
) -> tuple[float, float, float, float]:
    q_low, q_high = [float(value) for value in parameter_config["q_bounds"]]
    u0 = (
        2.0 * math.log(float(structure.lattice.a))
        + math.log(float(structure.lattice.c))
    ) / 3.0
    v0 = math.log(float(structure.lattice.c) / float(structure.lattice.a))
    values: list[tuple[float, float]] = []
    for q_u, q_v in itertools.product((q_low, q_high), repeat=2):
        u = u0 + q_u * float(parameter_config["du_half_range"])
        v = v0 + q_v * float(parameter_config["dv_half_range"])
        values.append((math.exp(u - v / 3.0), math.exp(u + 2.0 * v / 3.0)))
    return (
        min(value[0] for value in values),
        max(value[0] for value in values),
        min(value[1] for value in values),
        max(value[1] for value in values),
    )


def enumerate_reciprocal_superset(
    structure: Structure,
    *,
    grid_config: Mapping[str, Any],
    parameter_config: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Enumerate every integer hkl that can enter the padded q-domain window.

    Returns individual reflection indices, their deterministic group mapping,
    and the unique tetragonal metric terms H=h^2+k^2 and L=l^2.  Individual
    structure-factor intensities are summed only after evaluation, avoiding the
    incorrect assumption that one representative intensity times multiplicity
    is exact for every stored structure.
    """

    a_min, a_max, c_min, c_max = _lattice_extrema(structure, parameter_config)
    padding = float(grid_config.get("peak_calculation_padding_deg", 0.0))
    two_theta_min = float(grid_config["two_theta_min"]) - padding
    two_theta_max = float(grid_config["two_theta_max"]) + padding
    wavelength = float(grid_config["wavelength_angstrom"])
    minimum_radius = 2.0 * math.sin(math.radians(two_theta_min / 2.0)) / wavelength
    maximum_radius = 2.0 * math.sin(math.radians(two_theta_max / 2.0)) / wavelength
    h_limit = int(math.ceil(maximum_radius * a_max))
    l_limit = int(math.ceil(maximum_radius * c_max))

    reflections: list[tuple[int, int, int]] = []
    for h in range(-h_limit, h_limit + 1):
        for k in range(-h_limit, h_limit + 1):
            for ell in range(-l_limit, l_limit + 1):
                if h == 0 and k == 0 and ell == 0:
                    continue
                transverse = h * h + k * k
                longitudinal = ell * ell
                radius_min = math.sqrt(
                    transverse / (a_max * a_max)
                    + longitudinal / (c_max * c_max)
                )
                radius_max = math.sqrt(
                    transverse / (a_min * a_min)
                    + longitudinal / (c_min * c_min)
                )
                if radius_max >= minimum_radius and radius_min <= maximum_radius:
                    reflections.append((h, k, ell))
    if not reflections:
        raise ValueError("reciprocal superset is empty")

    reflections.sort(
        key=lambda hkl: (hkl[0] * hkl[0] + hkl[1] * hkl[1], hkl[2] * hkl[2], hkl)
    )
    hkl_array = np.asarray(reflections, dtype=np.int64)
    keys = [
        (int(h * h + k * k), int(ell * ell))
        for h, k, ell in hkl_array.tolist()
    ]
    unique_keys = sorted(set(keys))
    key_to_index = {key: index for index, key in enumerate(unique_keys)}
    group_indices = np.asarray([key_to_index[key] for key in keys], dtype=np.int64)
    group_h = np.asarray([key[0] for key in unique_keys], dtype=np.float64)
    group_l = np.asarray([key[1] for key in unique_keys], dtype=np.float64)
    return hkl_array, group_indices, group_h, group_l


class CachedTetragonalGPUForward:
    """One-parent clean forward with cached structure constants on CUDA."""

    def __init__(
        self,
        structure: Structure,
        *,
        grid_config: Mapping[str, Any],
        parameter_config: Mapping[str, Any],
        device: str = "cuda",
        dtype: torch.dtype = torch.float64,
    ) -> None:
        if dtype is not torch.float64:
            raise ValueError("Week-1 numerical gates require torch.float64")
        resolved_device = torch.device(device)
        if resolved_device.type != "cuda":
            raise ValueError("GPU-first Week-1 gates require a CUDA device")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available to PyTorch")
        if abs(float(structure.lattice.a) - float(structure.lattice.b)) > 1e-6:
            raise ValueError("GPU forward requires a conventional tetragonal lattice")

        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)

        self.structure = structure
        self.grid_config = dict(grid_config)
        self.parameter_config = dict(parameter_config)
        self.device = resolved_device
        self.dtype = dtype
        self.wavelength = float(grid_config["wavelength_angstrom"])
        self.calculation_min = float(grid_config["two_theta_min"]) - float(
            grid_config.get("peak_calculation_padding_deg", 0.0)
        )
        self.calculation_max = float(grid_config["two_theta_max"]) + float(
            grid_config.get("peak_calculation_padding_deg", 0.0)
        )
        self.u0 = (
            2.0 * math.log(float(structure.lattice.a))
            + math.log(float(structure.lattice.c))
        ) / 3.0
        self.v0 = math.log(float(structure.lattice.c) / float(structure.lattice.a))
        self.log_fwhm_center = 0.5 * (
            math.log(float(parameter_config["fwhm_min_deg"]))
            + math.log(float(parameter_config["fwhm_max_deg"]))
        )
        self.log_fwhm_half_range = 0.5 * (
            math.log(float(parameter_config["fwhm_max_deg"]))
            - math.log(float(parameter_config["fwhm_min_deg"]))
        )

        hkl, group_indices, group_h, group_l = enumerate_reciprocal_superset(
            structure,
            grid_config=grid_config,
            parameter_config=parameter_config,
        )
        atomic_numbers, coefficients, phase_real, phase_imag = (
            _element_scattering_arrays(structure, hkl)
        )
        group_membership = np.zeros(
            (len(hkl), len(group_h)), dtype=np.float64
        )
        group_membership[np.arange(len(hkl)), group_indices] = 1.0

        self.hkl = torch.as_tensor(hkl, device=self.device, dtype=self.dtype)
        self.reflection_h = self.hkl[:, 0].square() + self.hkl[:, 1].square()
        self.reflection_l = self.hkl[:, 2].square()
        self.group_h = torch.as_tensor(group_h, device=self.device, dtype=self.dtype)
        self.group_l = torch.as_tensor(group_l, device=self.device, dtype=self.dtype)
        self.group_membership = torch.as_tensor(
            group_membership, device=self.device, dtype=self.dtype
        )
        self.atomic_numbers = torch.as_tensor(
            atomic_numbers, device=self.device, dtype=self.dtype
        )
        self.coefficient_a = torch.as_tensor(
            coefficients[:, :, 0], device=self.device, dtype=self.dtype
        )
        self.coefficient_b = torch.as_tensor(
            coefficients[:, :, 1], device=self.device, dtype=self.dtype
        )
        self.element_phase_real = torch.as_tensor(
            phase_real, device=self.device, dtype=self.dtype
        )
        self.element_phase_imag = torch.as_tensor(
            phase_imag, device=self.device, dtype=self.dtype
        )
        self.axis = torch.as_tensor(
            _axis_values(grid_config), device=self.device, dtype=self.dtype
        )

    @property
    def reflection_count(self) -> int:
        return int(self.hkl.shape[0])

    @property
    def peak_group_count(self) -> int:
        return int(self.group_h.shape[0])

    def provenance(self) -> GPUForwardProvenance:
        index = self.device.index if self.device.index is not None else torch.cuda.current_device()
        return GPUForwardProvenance(
            contract=TORCH_FORWARD_CONTRACT,
            torch_version=str(torch.__version__),
            cuda_runtime=torch.version.cuda,
            device=str(self.device),
            device_name=torch.cuda.get_device_name(index),
            dtype=str(self.dtype).replace("torch.", ""),
            reflection_count=self.reflection_count,
            peak_group_count=self.peak_group_count,
            gaussian_support="cpu_floor_ceil_5sigma_with_float32_staging",
        )

    def q_to_physical_tensors(
        self, q: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if q.shape[-1] != 4:
            raise ValueError("q must end in four parameters")
        u = self.u0 + q[..., 0] * float(
            self.parameter_config["du_half_range"]
        )
        v = self.v0 + q[..., 1] * float(
            self.parameter_config["dv_half_range"]
        )
        a = torch.exp(u - v / 3.0)
        c = torch.exp(u + 2.0 * v / 3.0)
        delta = q[..., 2] * float(
            self.parameter_config["delta_half_range_deg"]
        )
        fwhm = torch.exp(
            self.log_fwhm_center + q[..., 3] * self.log_fwhm_half_range
        )
        return a, c, delta, fwhm

    def render(
        self,
        q: torch.Tensor,
        *,
        compatibility: bool = True,
        normalization_index: int | None = None,
    ) -> torch.Tensor:
        """Render one q vector or a batch.

        ``compatibility=True`` reproduces the CPU P0 oracle, including its
        display-level weak-peak cutoff, 5-sigma truncation, and float32 staging.
        The differentiable Gate view disables only those three numerical
        discontinuities; crystallography, intensity equations, axis, and
        parameterization remain identical.
        """

        single = q.ndim == 1
        batch = q.unsqueeze(0) if single else q
        if batch.ndim != 2 or batch.shape[1] != 4:
            raise ValueError("q must have shape (4,) or (batch, 4)")
        if batch.device != self.device or batch.dtype != self.dtype:
            batch = batch.to(device=self.device, dtype=self.dtype)
        a, c, delta, fwhm = self.q_to_physical_tensors(batch)

        reflection_g = torch.sqrt(
            self.reflection_h.unsqueeze(0) / a.square().unsqueeze(1)
            + self.reflection_l.unsqueeze(0) / c.square().unsqueeze(1)
        )
        reflection_s2 = (reflection_g / 2.0).square()
        scattering_sum = (
            self.coefficient_a.unsqueeze(0).unsqueeze(0)
            * torch.exp(
                -self.coefficient_b.unsqueeze(0).unsqueeze(0)
                * reflection_s2.unsqueeze(2).unsqueeze(3)
            )
        ).sum(dim=3)
        scattering_factor = self.atomic_numbers.unsqueeze(0).unsqueeze(0) - (
            41.78214 * reflection_s2.unsqueeze(2) * scattering_sum
        )
        structure_real = (
            scattering_factor * self.element_phase_real.unsqueeze(0)
        ).sum(dim=2)
        structure_imag = (
            scattering_factor * self.element_phase_imag.unsqueeze(0)
        ).sum(dim=2)

        reflection_argument = self.wavelength * reflection_g / 2.0
        reflection_theta = torch.asin(
            torch.clamp(reflection_argument, max=1.0 - 1e-12)
        )
        lorentz = (
            1.0 + torch.cos(2.0 * reflection_theta).square()
        ) / (torch.sin(reflection_theta).square() * torch.cos(reflection_theta))
        reflection_intensity = (
            structure_real.square() + structure_imag.square()
        ) * lorentz
        group_intensity = reflection_intensity @ self.group_membership

        group_g = torch.sqrt(
            self.group_h.unsqueeze(0) / a.square().unsqueeze(1)
            + self.group_l.unsqueeze(0) / c.square().unsqueeze(1)
        )
        group_argument = self.wavelength * group_g / 2.0
        group_theta = torch.asin(torch.clamp(group_argument, max=1.0 - 1e-12))
        group_two_theta = torch.rad2deg(2.0 * group_theta)
        valid = (
            (group_argument > 0.0)
            & (group_argument < 1.0)
            & (group_two_theta >= self.calculation_min)
            & (group_two_theta <= self.calculation_max)
        )
        group_intensity = group_intensity * valid.to(self.dtype)
        # Pymatgen drops scaled peaks at or below 0.001 on a 0--100
        # intensity scale, i.e. raw intensity <= 1e-5 of the strongest valid
        # peak.  Keeping these reflections produces profile discrepancies of
        # almost exactly 1e-5 on complex parents.
        if compatibility:
            strongest = group_intensity.amax(dim=1, keepdim=True)
            scaled_keep = group_intensity > strongest * 1.0e-5
            group_intensity = group_intensity * scaled_keep.to(self.dtype)
        centers = group_two_theta + delta.unsqueeze(1)

        sigma = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        z = (
            self.axis.unsqueeze(0).unsqueeze(0) - centers.unsqueeze(2)
        ) / sigma.unsqueeze(1).unsqueeze(2)
        # Mirror render_gaussian_peaks exactly.  Its support is not simply
        # abs(z)<=5: each peak uses floor/ceil index bounds and includes the
        # upper endpoint.  This discrete mask is intentionally piecewise
        # constant while the in-window Gaussian remains differentiable.
        grid_step = float(self.grid_config["step"])
        grid_minimum = float(self.grid_config["two_theta_min"])
        radius = 5.0 * sigma
        lower = torch.floor(
            (centers - radius.unsqueeze(1) - grid_minimum) / grid_step
        ).clamp(min=0, max=len(self.axis))
        upper = (
            torch.ceil(
                (centers + radius.unsqueeze(1) - grid_minimum) / grid_step
            )
            + 1.0
        ).clamp(min=0, max=len(self.axis))
        grid_indices = torch.arange(
            len(self.axis), device=self.device, dtype=self.dtype
        ).view(1, 1, -1)
        support = (grid_indices >= lower.unsqueeze(2)) & (
            grid_indices < upper.unsqueeze(2)
        )
        gaussian = (
            group_intensity.unsqueeze(2)
            / sigma.unsqueeze(1).unsqueeze(2)
            * torch.exp(-0.5 * z.square())
        )
        if compatibility:
            gaussian = gaussian * support.to(self.dtype)
        raw = gaussian.sum(dim=1)
        # The CPU oracle stages the unnormalized Gaussian sum through
        # float32 and returns a final float32-normalized profile.  Preserve
        # that compatibility boundary while keeping crystallography and the
        # Gaussian calculation themselves in float64.
        if compatibility:
            raw = raw.to(torch.float32).to(self.dtype)
        if not compatibility and normalization_index is not None:
            if not 0 <= normalization_index < raw.shape[1]:
                raise ValueError("normalization_index is outside the profile axis")
            maximum = raw[:, normalization_index : normalization_index + 1]
        else:
            maximum = raw.amax(dim=1, keepdim=True)
        normalized = raw / torch.clamp_min(maximum, torch.finfo(self.dtype).tiny)
        if compatibility:
            normalized = normalized.to(torch.float32).to(self.dtype)
        return normalized[0] if single else normalized

    def transformed(
        self, q: torch.Tensor, *, normalization_index: int | None = None
    ) -> torch.Tensor:
        return torch.log1p(
            100.0
            * self.render(
                q,
                compatibility=False,
                normalization_index=normalization_index,
            )
        ) / math.log(101.0)

    def smooth_normalization_index(self, q: Sequence[float]) -> int:
        """Return the sampled max branch used for a local derivative audit."""

        values = np.asarray(q, dtype=np.float64)
        if values.shape != (4,):
            raise ValueError("normalization reference q must be a four-vector")
        with torch.no_grad():
            tensor = torch.as_tensor(values, device=self.device, dtype=self.dtype)
            profile = self.render(tensor, compatibility=False)
        return int(torch.argmax(profile).item())

    def render_numpy(
        self,
        q: Sequence[float] | np.ndarray,
        *,
        compatibility: bool = True,
    ) -> np.ndarray:
        values = np.asarray(q, dtype=np.float64)
        q_low, q_high = [
            float(value) for value in self.parameter_config["q_bounds"]
        ]
        if values.shape[-1] != 4 or np.any(values < q_low) or np.any(values > q_high):
            raise ValueError("q is outside the frozen four-parameter domain")
        with torch.no_grad():
            tensor = torch.as_tensor(values, device=self.device, dtype=self.dtype)
            return self.render(tensor, compatibility=compatibility).cpu().numpy()

    def transformed_numpy(
        self,
        q: Sequence[float] | np.ndarray,
        *,
        normalization_index: int | None = None,
    ) -> np.ndarray:
        values = np.asarray(q, dtype=np.float64)
        q_low, q_high = [
            float(value) for value in self.parameter_config["q_bounds"]
        ]
        if values.shape[-1] != 4 or np.any(values < q_low) or np.any(values > q_high):
            raise ValueError("q is outside the frozen four-parameter domain")
        with torch.no_grad():
            tensor = torch.as_tensor(values, device=self.device, dtype=self.dtype)
            return self.transformed(
                tensor, normalization_index=normalization_index
            ).cpu().numpy()

    def transformed_jacobian_numpy(
        self,
        q: Sequence[float],
        *,
        normalization_index: int | None = None,
    ) -> np.ndarray:
        values = np.asarray(q, dtype=np.float64)
        if values.shape != (4,):
            raise ValueError("Jacobian q must be a four-vector")
        tensor = torch.as_tensor(values, device=self.device, dtype=self.dtype)
        with torch.autocast(device_type="cuda", enabled=False):
            jacobian = torch.func.jacfwd(
                lambda value: self.transformed(
                    value, normalization_index=normalization_index
                )
            )(tensor)
        output = jacobian.detach().cpu().numpy()
        if output.shape != (len(self.axis), 4) or not np.isfinite(output).all():
            raise RuntimeError("CUDA autograd produced an invalid Jacobian")
        return output

    def transformed_and_jacobian_numpy(
        self, q: Sequence[float]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return a transformed profile and forward-mode Jacobian in one graph."""

        values = np.asarray(q, dtype=np.float64)
        if values.shape != (4,):
            raise ValueError("Jacobian q must be a four-vector")
        tensor = torch.as_tensor(values, device=self.device, dtype=self.dtype)

        def with_aux(value: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            transformed = self.transformed(value)
            return transformed, transformed

        with torch.autocast(device_type="cuda", enabled=False):
            jacobian, transformed = torch.func.jacfwd(with_aux, has_aux=True)(tensor)
        profile_output = transformed.detach().cpu().numpy()
        jacobian_output = jacobian.detach().cpu().numpy()
        if (
            profile_output.shape != (len(self.axis),)
            or jacobian_output.shape != (len(self.axis), 4)
            or not np.isfinite(profile_output).all()
            or not np.isfinite(jacobian_output).all()
        ):
            raise RuntimeError("CUDA autograd produced an invalid profile/Jacobian pair")
        return profile_output, jacobian_output
