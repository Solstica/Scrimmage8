// 从固定结果提取 Origin 用表；只重排，不求解、不插值。
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { Workbook } from '@oai/artifact-tool';

const root = process.argv[2] ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const q1 = path.join(root, 'modules/20_q1');
const formal = path.join(q1, 'results/formal_run_20260826_v2');
const out = path.join(q1, 'figures/editable');
const preview = process.argv[3];

async function read(file) {
  const wb = await Workbook.fromCSV((await fs.readFile(file, 'utf8')).replace(/^\uFEFF/, ''), {sheetName: '数据'});
  const [header, ...rows] = wb.worksheets.getItemAt(0).getUsedRange().values;
  return rows.filter(row => row[0] !== null && row[0] !== '').map(row =>
    Object.fromEntries(header.map((name, i) => [name, Number(row[i])])));
}

async function save(name, rows, matrix = false) {
  const wb = Workbook.create();
  const sheet = wb.worksheets.add(name);
  sheet.getRangeByIndexes(0, 0, rows.length, rows[0].length).values = rows;
  const actual = sheet.getUsedRange().values;
  assert.deepEqual(actual, rows);
  // 仅序列化工作表数值，不采用显示小数位，不截断原始结果精度。
  const cell = value => value == null ? '' : String(value);
  const csv = '\uFEFF' + actual.map(row => row.map(cell).join(',')).join('\r\n') + '\r\n';
  await fs.writeFile(path.join(out, name + '.csv'), csv, 'utf8');
  if (preview) {
    sheet.getUsedRange().format.columnWidth = matrix ? 14 : 24;
    sheet.getUsedRange().format.rowHeight = 23;
    sheet.getUsedRange().setNumberFormat('0.000');
    sheet.getRangeByIndexes(0, 0, 1, rows[0].length).format.fill = '#E8EFF5';
    if (matrix) sheet.getRangeByIndexes(0, 0, 1, rows[0].length).setNumberFormat('0.##');
    const png = await wb.render({sheetName: name, range: matrix ? 'A1:H8' : `A1:${rows[0].length === 5 ? 'E8' : 'F5'}`, scale: 1.4, format: 'png'});
    await fs.mkdir(preview, {recursive: true});
    await fs.writeFile(path.join(preview, name + '.png'), new Uint8Array(await png.arrayBuffer()));
  }
  console.log(`${name}: ${rows.length} 行 × ${rows[0].length} 列，回读一致`);
}

const history = (await read(path.join(formal, 'q1_temperature_history.csv')))
  .filter(row => row['扫描速率（K/min）'] === 5);
assert.equal(history.length, 1246);
const sourceNames = ['时间（s）', '贴身侧温度（℃）', '功能层平均温度（℃）', '外表面温度（℃）', '固化进度'];
const curves = [['时间（s）', '贴身侧温度（℃）', '功能层均温（℃）', '外表面温度（℃）', '固化进度'],
  ...history.map(row => sourceNames.map(name => row[name]))];

const profiles = await read(path.join(formal, 'q1_temperature_profiles.csv'));
const times = [...new Set(profiles.map(row => row['时间（s）']))].sort((a, b) => a - b);
const positions = [...new Set(profiles.map(row => row['距人体侧位置（m）']))].sort((a, b) => a - b);
assert.equal(times.length, 33);
assert.equal(positions.length, 91);
const field = new Map();
for (const row of profiles) {
  const key = `${row['时间（s）']},${row['距人体侧位置（m）']}`;
  const value = row['温度（℃）'];
  if (field.has(key)) assert.ok(Math.abs(field.get(key) - value) < 1e-8);
  field.set(key, value);
}
// 首行 X=时间，首列 Y=位置（mm），Z=温度（℃）；不补齐成等距坐标。
const matrix = [[null, ...times], ...positions.map(x => [x * 1000, ...times.map(t => field.get(`${t},${x}`))])];
assert.equal(field.size, 33 * 91);

const rates = await read(path.join(formal, 'q1_results.csv'));
const initials = await read(path.join(q1, 'results/EXPERIMENT/initial_temperature_sensitivity_20260827/q1_initial_temperature_results.csv'));
assert.deepEqual(rates.map(row => row['扫描速率（K/min）']), [2, 5, 10]);
assert.deepEqual(initials.map(row => row['衣料初温（℃）']), [27, 30, 33, 37]);
// Origin 长名称可重名；同一指标在两个面板中用相同图例名。
const sensitivity = [['扫描速率（K/min）', 't₁₅（s）', 't₁₀（s）', '衣料初温（℃）', 't₁₅（s）', 't₁₀（s）'],
  ...initials.map((row, i) => [rates[i]?.['扫描速率（K/min）'] ?? null,
    rates[i]?.['t15（s）'] ?? null, rates[i]?.['t10（s）'] ?? null,
    row['衣料初温（℃）'], row['t15（s）'], row['t10（s）']])];

for (const table of [curves, matrix, sensitivity]) {
  for (const row of table.slice(1)) for (const value of row) {
    assert.ok(value === null || Number.isFinite(value));
  }
}
await save('温度场矩阵', matrix, true);
await save('温度与固化曲线', curves);
await save('敏感性分析', sensitivity);
