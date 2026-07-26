from __future__ import annotations

import unittest

from xrd_robustness.training.early_stopping import (
    EarlyStoppingState,
    update_early_stopping,
)


class EarlyStoppingTest(unittest.TestCase):
    def test_primary_improvement_resets_patience(self) -> None:
        state = EarlyStoppingState()
        save, stop = update_early_stopping(
            state,
            epoch=5,
            global_step=3080,
            primary=0.4,
            validation_id=0.5,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        self.assertTrue(save)
        self.assertFalse(stop)
        for epoch in (10, 15, 20):
            update_early_stopping(
                state,
                epoch=epoch,
                global_step=epoch * 616,
                primary=0.4005,
                validation_id=0.5,
                min_delta=0.001,
                patience=4,
                min_epochs=50,
            )
        self.assertEqual(state.checks_without_primary_improvement, 3)
        save, _ = update_early_stopping(
            state,
            epoch=25,
            global_step=15400,
            primary=0.402,
            validation_id=0.49,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        self.assertTrue(save)
        self.assertEqual(state.checks_without_primary_improvement, 0)

    def test_id_tie_updates_best_without_resetting_patience(self) -> None:
        state = EarlyStoppingState()
        update_early_stopping(
            state,
            epoch=5,
            global_step=3080,
            primary=0.4,
            validation_id=0.5,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        save, stop = update_early_stopping(
            state,
            epoch=10,
            global_step=6160,
            primary=0.4005,
            validation_id=0.51,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        self.assertTrue(save)
        self.assertFalse(stop)
        self.assertEqual(state.best_epoch, 10)
        self.assertEqual(state.checks_without_primary_improvement, 1)

    def test_id_tie_does_not_lower_primary_improvement_reference(self) -> None:
        state = EarlyStoppingState()
        update_early_stopping(
            state,
            epoch=5,
            global_step=3080,
            primary=0.5,
            validation_id=0.5,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        update_early_stopping(
            state,
            epoch=10,
            global_step=6160,
            primary=0.4995,
            validation_id=0.6,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        save, _ = update_early_stopping(
            state,
            epoch=15,
            global_step=9240,
            primary=0.5006,
            validation_id=0.4,
            min_delta=0.001,
            patience=4,
            min_epochs=50,
        )
        self.assertFalse(save)
        self.assertEqual(state.primary_improvement_reference, 0.5)
        self.assertEqual(state.checks_without_primary_improvement, 2)

    def test_minimum_epoch_gate_can_stop_at_fifty(self) -> None:
        state = EarlyStoppingState()
        for epoch in range(5, 55, 5):
            _, stop = update_early_stopping(
                state,
                epoch=epoch,
                global_step=epoch * 616,
                primary=0.5,
                validation_id=0.6,
                min_delta=0.001,
                patience=4,
                min_epochs=50,
            )
            if epoch < 50:
                self.assertFalse(stop)
        self.assertTrue(stop)
        self.assertEqual(state.stop_epoch, 50)

    def test_state_round_trip(self) -> None:
        state = EarlyStoppingState(best_epoch=25, best_primary=0.7)
        self.assertEqual(
            EarlyStoppingState.from_mapping(state.to_dict()).to_dict(),
            state.to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
