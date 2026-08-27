import csv
import math
import sys
from pathlib import Path


def read(path):
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    modal = read(src / "外对流核算.csv")
    fvm = read(src / "外对流有限体积验证.csv")
    names = ["ISO 11079简化", "旧PMV关系", "Kuwabara经验"]
    keys = {(name, scan) for name in names for scan in (2.0, 5.0, 10.0)}
    index = {(r["外对流模型"], float(r["扫描速率（K/min）"])): r for r in modal}
    if len(modal) != 9 or set(index) != keys:
        raise ValueError("模态核算必须恰好覆盖九个工况")

    time_rows, sens_rows, check_rows = [], [], []
    for scan in (2.0, 5.0, 10.0):
        ref = index["ISO 11079简化", scan]
        for name in names:
            r = index[name, scan]
            h, t15, t10 = (float(r[k]) for k in ("h_e（W/(m2 K)）", "t15（s）", "t10（s）"))
            if not all(math.isfinite(v) for v in (h, t15, t10)) or not 0 < t15 < t10:
                raise ValueError("阈值时间不合法")
            time_rows.append([name, h, scan, t15, t10, t10 - t15])
            change = [100 * (float(r[f"t{k}（s）"]) / float(ref[f"t{k}（s）"]) - 1) for k in (15, 10)]
            if not all(math.isfinite(value) for value in change):
                raise ValueError("敏感性复算得到非有限数值")
            if name != "ISO 11079简化":
                sens_rows.append([name, scan, *change])

    base = {(r["外对流模型"], float(r["扫描速率（K/min）"])): r for r in fvm if r["设置"] == "基准"}
    if len(fvm) != 11 or len(base) != 9 or set(base) != keys:
        raise ValueError("有限体积验证应包含九组基准及两组加密")
    for r in fvm:
        name, scan = r["外对流模型"], float(r["扫描速率（K/min）"])
        for k in (15, 10):
            modal_t = float(index[name, scan][f"t{k}（s）"])
            if not math.isclose(modal_t, float(r[f"模态t{k}（s）"]), abs_tol=1e-10):
                raise ValueError("验证与模态结果版本不一致")
            ref_t = modal_t if r["设置"] == "基准" else float(base[name, scan][f"有限体积t{k}（s）"])
            delta = 100 * (float(r[f"有限体积t{k}（s）"]) / ref_t - 1)
            key = f"t{k}较模态偏差（%）" if r["设置"] == "基准" else f"t{k}较基准有限体积变化（%）"
            if not math.isfinite(delta) or not math.isclose(delta, float(r[key]), abs_tol=1e-10):
                raise ValueError("数值验证复算与原表不符")
            check_rows.append([r["设置"], name, scan, f"t{k}", delta, abs(delta)])

    save(out / "阈值时间.csv", ["外对流模型", "h_e（W/(m2 K)）", "扫描速率（K/min）", "t15（s）", "t10（s）", "阈值间隔（s）"], time_rows)
    save(out / "边界敏感性.csv", ["外对流模型", "扫描速率（K/min）", "t15变化（%）", "t10变化（%）"], sens_rows)
    save(out / "数值验证.csv", ["设置", "外对流模型", "扫描速率（K/min）", "阈值", "相对差异（%）", "绘图幅值（%）"], check_rows)
    print("逐图数据复算通过：阈值 9 行，敏感性 6 行，数值验证 22 行；无平滑、拟合或抽样。")


if __name__ == "__main__":
    main()
