# 探索性独立渲染压力测试

状态：PASS。在主测试打开后另行登记；不替代或挽救主要结果。

独立 pymatgen 峰表、伪 Voigt 峰形与未建模二次背景；每材料 16 个新父样本，无重训。

- batio3: PASS
  N+A seed=2026101911: q MAE=0.00266487, cell MAE (Å)=[6.40424467888423e-05, 0.0003644653931485775], mean seconds=0.097898, convergence=1.000
  N+A seed=2026101912: q MAE=0.0026651, cell MAE (Å)=[6.407232986727074e-05, 0.0003644727697903749], mean seconds=0.0956345, convergence=1.000
  N+A seed=2026101913: q MAE=0.0026649, cell MAE (Å)=[6.408209079611371e-05, 0.00036442986847928793], mean seconds=0.0962738, convergence=1.000
  P0 seed=0: q MAE=0.00266497, cell MAE (Å)=[6.407011598233425e-05, 0.00036445411589403065], mean seconds=0.108437, convergence=1.000
  P3 seed=0: q MAE=0.00266512, cell MAE (Å)=[6.406069911463197e-05, 0.0003644881486138951], mean seconds=0.334347, convergence=1.000
- mgo: PASS
  N+A seed=2026101911: q MAE=0.00166721, cell MAE (Å)=[0.0001404457812555493], mean seconds=0.0511541, convergence=1.000
  N+A seed=2026101912: q MAE=0.00166423, cell MAE (Å)=[0.00014019497288225713], mean seconds=0.0539091, convergence=1.000
  N+A seed=2026101913: q MAE=0.00166451, cell MAE (Å)=[0.0001402187351748907], mean seconds=0.0493366, convergence=1.000
  P0 seed=0: q MAE=0.00166383, cell MAE (Å)=[0.000140160937231959], mean seconds=0.0665402, convergence=1.000
  P3 seed=0: q MAE=0.00166441, cell MAE (Å)=[0.0001402100864899558], mean seconds=0.204011, convergence=1.000
- ceo2: PASS
  N+A seed=2026101911: q MAE=0.00104084, cell MAE (Å)=[0.00011263940435762843], mean seconds=0.0713531, convergence=1.000
  N+A seed=2026101912: q MAE=0.0010409, cell MAE (Å)=[0.00011264610747324655], mean seconds=0.0694139, convergence=1.000
  N+A seed=2026101913: q MAE=0.00104009, cell MAE (Å)=[0.00011255823406730592], mean seconds=0.0693444, convergence=1.000
  P0 seed=0: q MAE=0.00104055, cell MAE (Å)=[0.00011260879249269662], mean seconds=0.0756612, convergence=1.000
  P3 seed=0: q MAE=0.00104044, cell MAE (Å)=[0.00011259589843787277], mean seconds=0.257842, convergence=1.000
- rutile: PASS
  N+A seed=2026101911: q MAE=0.00109245, cell MAE (Å)=[7.774888832301485e-05, 7.921306474992229e-05], mean seconds=0.10722, convergence=1.000
  N+A seed=2026101912: q MAE=0.00109253, cell MAE (Å)=[7.779354982012654e-05, 7.919391376121077e-05], mean seconds=0.10396, convergence=1.000
  N+A seed=2026101913: q MAE=0.00109222, cell MAE (Å)=[7.769826180864525e-05, 7.921887201789435e-05], mean seconds=0.107837, convergence=1.000
  P0 seed=0: q MAE=0.00109309, cell MAE (Å)=[7.781981426790985e-05, 7.924350090732224e-05], mean seconds=0.11775, convergence=1.000
  P3 seed=0: q MAE=0.00109303, cell MAE (Å)=[7.780039148819196e-05, 7.924839732817435e-05], mean seconds=0.392471, convergence=1.000
- zno: PASS
  N+A seed=2026101911: q MAE=0.00134172, cell MAE (Å)=[8.088002292183649e-05, 0.0001498489576783335], mean seconds=0.0823002, convergence=1.000
  N+A seed=2026101912: q MAE=0.00133979, cell MAE (Å)=[8.07016131904037e-05, 0.0001497327623746214], mean seconds=0.0782108, convergence=1.000
  N+A seed=2026101913: q MAE=0.00134007, cell MAE (Å)=[8.081384698341298e-05, 0.00014961143238068075], mean seconds=0.0807469, convergence=1.000
  P0 seed=0: q MAE=0.00134085, cell MAE (Å)=[8.083058384730779e-05, 0.00014974702581860289], mean seconds=0.0964997, convergence=1.000
  P3 seed=0: q MAE=0.00134033, cell MAE (Å)=[8.079861785717513e-05, 0.00014968830729555904], mean seconds=0.336131, convergence=1.000
- silicon: PASS
  N+A seed=2026101911: q MAE=0.00143083, cell MAE (Å)=[0.00015540828118615346], mean seconds=0.0680258, convergence=1.000
  N+A seed=2026101912: q MAE=0.00143107, cell MAE (Å)=[0.00015543398338785375], mean seconds=0.0680782, convergence=1.000
  N+A seed=2026101913: q MAE=0.00143172, cell MAE (Å)=[0.00015550507270822855], mean seconds=0.0676852, convergence=1.000
  P0 seed=0: q MAE=0.00143103, cell MAE (Å)=[0.00015543007733659353], mean seconds=0.0743338, convergence=1.000
  P3 seed=0: q MAE=0.00143139, cell MAE (Å)=[0.00015546920829256905], mean seconds=0.243108, convergence=1.000
- grossular: PASS
  N+A seed=2026101911: q MAE=0.000953989, cell MAE (Å)=[0.0002260380951560892], mean seconds=0.33019, convergence=1.000
  N+A seed=2026101912: q MAE=0.000953342, cell MAE (Å)=[0.0002258849302541055], mean seconds=0.354639, convergence=1.000
  N+A seed=2026101913: q MAE=0.000953738, cell MAE (Å)=[0.00022597858742146038], mean seconds=0.344614, convergence=1.000
  P0 seed=0: q MAE=0.000953722, cell MAE (Å)=[0.00022597494933129791], mean seconds=0.422716, convergence=1.000
  P3 seed=0: q MAE=0.000954034, cell MAE (Å)=[0.00022604883253174446], mean seconds=1.26752, convergence=1.000
