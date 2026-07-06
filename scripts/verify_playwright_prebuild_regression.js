const fs = require('fs');
const path = require('path');
const mcp = require(path.resolve(__dirname, '..', 'tools', 'playwright-mcp', 'node_modules', 'playwright-core', 'lib', 'mcpBundle'));
const { chromium } = require(path.resolve(__dirname, '..', 'tools', 'playwright-mcp', 'node_modules', 'playwright-core'));

const repoRoot = path.resolve(__dirname, '..');
const artifactDir = path.join(repoRoot, '.artifacts', 'playwright-prebuild-regression');
const outputDir = path.join(artifactDir, 'mcp-session');
const summaryPath = path.join(artifactDir, 'regression-summary.json');

const targetUrl = process.argv[2] || 'http://127.0.0.1:8506';
const systemResourcePath = process.argv[3];
const systemProcessPath = process.argv[4];
const inspectionLogPath = process.argv[5];
const spiCsvPath = process.argv[6];
const spiProcessResourcePath = process.argv[7];

fs.mkdirSync(outputDir, { recursive: true });

function textFromToolResult(result) {
  return (result.content || [])
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('\n');
}

function jsonFromToolResult(result) {
  const text = textFromToolResult(result).trim();
  if (!text) {
    throw new Error('Empty MCP tool result.');
  }

  try {
    return JSON.parse(text);
  } catch (error) {
  }

  const markdownMatch = text.match(/### Result\s*([\s\S]*?)\s*### Ran Playwright code/);
  if (markdownMatch && markdownMatch[1]) {
    return JSON.parse(markdownMatch[1].trim());
  }

  const objectMatch = text.match(/\{[\s\S]*\}$/);
  if (objectMatch) {
    return JSON.parse(objectMatch[0]);
  }

  throw new Error(`Could not parse JSON from MCP tool result: ${text}`);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function logStepStart(stepName, description, failureCondition) {
  console.log(`[STEP] ${stepName}`);
  console.log(`CHECK: ${description}`);
  console.log(`FAILS IF: ${failureCondition}`);
}

function logStepPass(stepName, stdoutPayload) {
  console.log(`STDOUT: ${JSON.stringify(stdoutPayload, null, 2)}`);
  console.log(`[PASS] ${stepName}`);
}

function logStepFail(stepName, error) {
  console.log(`[FAIL] ${stepName}`);
  console.log(`ERROR: ${error && (error.stack || error.message || String(error))}`);
}

async function main() {
  assert(systemResourcePath && fs.existsSync(systemResourcePath), `System resource CSV not found: ${systemResourcePath}`);
  assert(systemProcessPath && fs.existsSync(systemProcessPath), `System process CSV not found: ${systemProcessPath}`);
  assert(inspectionLogPath && fs.existsSync(inspectionLogPath), `Inspection log not found: ${inspectionLogPath}`);
  assert(spiCsvPath && fs.existsSync(spiCsvPath), `SPI tact-time CSV not found: ${spiCsvPath}`);
  assert(
    spiProcessResourcePath && fs.existsSync(spiProcessResourcePath),
    `SPI ProcessResource log not found: ${spiProcessResourcePath}`
  );

  const downloadDir = path.join(artifactDir, 'downloads');
  fs.mkdirSync(downloadDir, { recursive: true });

  const client = new mcp.Client({ name: 'pc-monitor-playwright-prebuild-regression', version: '0.1' });
  const transport = new mcp.StdioClientTransport({
    command: 'C:/Program Files/nodejs/node.exe',
    args: [
      path.join(repoRoot, 'tools', 'playwright-mcp', 'node_modules', '@playwright', 'mcp', 'cli.js'),
      '--browser=msedge',
      '--headless',
      '--isolated',
      '--output-mode=file',
      '--output-dir',
      outputDir,
    ],
    stderr: 'pipe',
    cwd: repoRoot,
  });

  const steps = [];
  const callTool = async (name, args = {}) => {
    const result = await client.callTool({ name, arguments: args });
    if (result.isError) {
      throw new Error(`${name} failed: ${textFromToolResult(result)}`);
    }
    return result;
  };

  async function runStep(stepName, description, failureCondition, runner) {
    logStepStart(stepName, description, failureCondition);
    try {
      const stdoutPayload = await runner();
      steps.push({
        name: stepName,
        description,
        failureCondition,
        ok: true,
        stdout: stdoutPayload,
      });
      logStepPass(stepName, stdoutPayload);
      return stdoutPayload;
    } catch (error) {
      const renderedError = error && (error.stack || error.message || String(error));
      steps.push({
        name: stepName,
        description,
        failureCondition,
        ok: false,
        error: renderedError,
      });
      logStepFail(stepName, error);
      throw error;
    }
  }

  async function waitForDirectInspectionPanel(page, sourceType) {
    await page.waitForFunction(
      (expectedSourceType) => {
        const bodyText = document.body.innerText;
        return (
          bodyText.includes(`감지된 로그 형식: ${expectedSourceType}`) &&
          bodyText.includes('검사 결과 XLSX 내보내기') &&
          document.querySelectorAll('input[type="number"]').length >= 2
        );
      },
      sourceType,
      { timeout: 90000 }
    );
  }

  async function directDownloadByButton(page, buttonName, savePath) {
    let lastError = null;

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        try {
          fs.unlinkSync(savePath);
        } catch (error) {
        }

        const button = page.getByRole('button', { name: buttonName }).first();
        await button.scrollIntoViewIfNeeded();
        await page.waitForTimeout(1000);
        const downloadPromise = page.waitForEvent('download', { timeout: 60000 });
        await button.click();
        const download = await downloadPromise;
        await download.saveAs(savePath);
        assert(fs.existsSync(savePath), `Download was not saved: ${savePath}`);
        const size = fs.statSync(savePath).size;
        assert(size > 0, `Download is empty: ${savePath}`);
        await page.waitForTimeout(1000);
        return {
          buttonName,
          attempt,
          suggestedFilename: download.suggestedFilename(),
          savedPath: savePath,
          size,
        };
      } catch (error) {
        lastError = error;
        await page.waitForTimeout(2000);
      }
    }

    throw lastError;
  }

  async function runDirectAoiDownloadFlow() {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const page = await browser.newPage({ acceptDownloads: true });
    try {
      await page.goto(targetUrl);
      await page.waitForTimeout(5000);
      await page.locator('input[type="file"]').nth(1).setInputFiles(inspectionLogPath);
      await waitForDirectInspectionPanel(page, 'AOI');

      const raw = await directDownloadByButton(
        page,
        '인스팩터 로그 다른 이름으로 저장',
        path.join(downloadDir, 'aoi-raw-log.download')
      );
      const parsed = await directDownloadByButton(
        page,
        '파싱된 AOI/SPI 로그 CSV 다운로드',
        path.join(downloadDir, 'aoi-parsed-log.csv')
      );

      const numberInputs = page.locator('input[type="number"]');
      const initialStartNo = await numberInputs.nth(0).inputValue();
      const initialEndNo = await numberInputs.nth(1).inputValue();
      const textInputs = page.locator('input[type="text"]');
      await textInputs.nth(0).fill('2026-03-19 00:00:00');
      await textInputs.nth(1).fill('2026-03-19 06:00:00');
      await textInputs.nth(1).press('Enter');

      let filteredStartNo = initialStartNo;
      let filteredEndNo = initialEndNo;
      for (let i = 0; i < 60; i += 1) {
        await page.waitForTimeout(1000);
        filteredStartNo = await numberInputs.nth(0).inputValue();
        filteredEndNo = await numberInputs.nth(1).inputValue();
        if (filteredStartNo !== initialStartNo || filteredEndNo !== initialEndNo) {
          break;
        }
      }
      assert(Number(filteredStartNo) > Number(initialStartNo), 'Direct AOI filtered start NO did not increase.');
      assert(Number(filteredEndNo) < Number(initialEndNo), 'Direct AOI filtered end NO did not decrease.');

      const workbook = await directDownloadByButton(
        page,
        '검사 결과 XLSX 다운로드',
        path.join(downloadDir, 'aoi-inspection-results.xlsx')
      );
      return {
        raw,
        parsed,
        workbook,
        initialStartNo,
        initialEndNo,
        filteredStartNo,
        filteredEndNo,
      };
    } finally {
      await browser.close();
    }
  }

  async function runDirectSpiDownloadFlow() {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    const page = await browser.newPage({ acceptDownloads: true });
    try {
      await page.goto(targetUrl);
      await page.waitForTimeout(5000);
      await page.locator('input[type="file"]').nth(1).setInputFiles([spiCsvPath, spiProcessResourcePath]);
      await waitForDirectInspectionPanel(page, 'SPI');

      const bodyText = await page.locator('body').innerText();
      assert(bodyText.includes('감지된 로그 형식: SPI'), 'SPI source type was not visible.');

      await page.screenshot({
        path: path.join(artifactDir, '08-spi-upload.png'),
        fullPage: true,
      });

      const numberInputs = page.locator('input[type="number"]');
      const startNo = await numberInputs.nth(0).inputValue();
      const endNo = await numberInputs.nth(1).inputValue();
      assert(Number(endNo) >= Number(startNo), 'SPI NO range is invalid.');

      const raw = await directDownloadByButton(
        page,
        '인스팩터 로그 다른 이름으로 저장',
        path.join(downloadDir, 'spi-raw-logs.zip')
      );
      const parsed = await directDownloadByButton(
        page,
        '파싱된 AOI/SPI 로그 CSV 다운로드',
        path.join(downloadDir, 'spi-parsed-log.csv')
      );
      const parsedText = fs.readFileSync(parsed.savedPath, 'utf-8');
      assert(parsedText.includes('SPI'), 'Downloaded SPI parsed CSV does not contain SPI source rows.');
      assert(
        parsedText.includes('23.411') || parsedText.includes('23.534'),
        'Downloaded SPI parsed CSV does not contain expected Total seconds.'
      );
      assert(
        parsedText.includes('0.465') || parsedText.includes('0.467'),
        'Downloaded SPI parsed CSV does not contain expected Frame seconds.'
      );
      const workbook = await directDownloadByButton(
        page,
        '검사 결과 XLSX 다운로드',
        path.join(downloadDir, 'spi-inspection-results.xlsx')
      );
      return {
        startNo,
        endNo,
        raw,
        parsed,
        workbook,
      };
    } finally {
      await browser.close();
    }
  }

  const artifacts = [
    '.artifacts/playwright-prebuild-regression/01-home.png',
    '.artifacts/playwright-prebuild-regression/02-cpu.png',
    '.artifacts/playwright-prebuild-regression/03-memory.png',
    '.artifacts/playwright-prebuild-regression/04-storage.png',
    '.artifacts/playwright-prebuild-regression/05-custom.png',
    '.artifacts/playwright-prebuild-regression/06-inspection-upload.png',
    '.artifacts/playwright-prebuild-regression/07-inspection-filter.png',
    '.artifacts/playwright-prebuild-regression/08-spi-upload.png',
    '.artifacts/playwright-prebuild-regression/downloads/aoi-raw-log.download',
    '.artifacts/playwright-prebuild-regression/downloads/aoi-parsed-log.csv',
    '.artifacts/playwright-prebuild-regression/downloads/aoi-inspection-results.xlsx',
    '.artifacts/playwright-prebuild-regression/downloads/spi-raw-logs.zip',
    '.artifacts/playwright-prebuild-regression/downloads/spi-parsed-log.csv',
    '.artifacts/playwright-prebuild-regression/downloads/spi-inspection-results.xlsx',
    '.artifacts/playwright-prebuild-regression/console-messages.md',
  ];

  try {
    await client.connect(transport);

    await runStep(
      'page-ready',
      'Streamlit app opens and the two upload inputs are available.',
      'The page does not open, fewer than two file inputs exist, or system upload cannot begin.',
      async () => {
        await callTool('browser_navigate', { url: targetUrl });
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            await page.waitForTimeout(8000);
            const fileInputCount = await page.locator('input[type="file"]').count();
            const bodyText = await page.locator('body').innerText();
            return {
              fileInputCount,
              title: await page.title(),
              bodyHasUploadSection: bodyText.includes('CSV') && bodyText.includes('LOG'),
            };
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.fileInputCount >= 2, `Expected at least 2 file inputs, got ${payload.fileInputCount}`);
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/01-home.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'system-log-upload',
      'System resource/process CSV uploads populate the dashboards.',
      'System file upload fails, dashboard select does not appear, or no charts render.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            await page.locator('input[type="file"]').nth(0).setInputFiles([
              ${JSON.stringify(systemResourcePath)},
              ${JSON.stringify(systemProcessPath)},
            ]);
            for (let i = 0; i < 40; i += 1) {
              await page.waitForTimeout(1000);
              const plotCount = await page.locator('.js-plotly-plot').count();
              const selectCount = await page.locator('[data-baseweb="select"]').count();
              const bodyText = await page.locator('body').innerText();
              if (plotCount > 0 && selectCount >= 2 && bodyText.includes('시스템 모니터 행')) {
                return {
                  plotCount,
                  selectCount,
                  systemRowsLoaded: bodyText.includes('시스템 모니터 행'),
                };
              }
            }
            throw new Error('Timed out waiting for uploaded system dashboards to render.');
          }`,
        });
        return jsonFromToolResult(result);
      }
    );

    await runStep(
      'cpu-dashboard',
      'CPU dashboard renders after system log upload.',
      'CPU heading or chart payload is missing.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            const heading = await page.getByRole('heading', { name: 'CPU 성능 및 온도' }).textContent();
            const plotCount = await page.locator('.js-plotly-plot').count();
            return { heading, plotCount };
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.plotCount >= 1, 'CPU dashboard plot count is 0.');
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/02-cpu.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'memory-dashboard',
      'Memory dashboard can be selected and rendered.',
      'Dashboard select fails, memory heading is missing, or no chart is shown.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            const select = page.locator('[data-baseweb="select"]').nth(1);
            await select.click();
            await page.getByRole('option', { name: '메모리 + 인스펙터 대시보드' }).click();
            await page.waitForTimeout(3000);
            const heading = await page.getByRole('heading', { name: '메모리 및 AOI/SPI 분석' }).textContent();
            const plotCount = await page.locator('.js-plotly-plot').count();
            return { heading, plotCount };
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.plotCount >= 1, 'Memory dashboard plot count is 0.');
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/03-memory.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'storage-dashboard',
      'Storage dashboard can be selected and rendered.',
      'Storage heading is missing or chart rendering fails.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            const select = page.locator('[data-baseweb="select"]').nth(1);
            await select.click();
            await page.getByRole('option', { name: '스토리지 대시보드' }).click();
            await page.waitForTimeout(3000);
            const heading = await page.getByRole('heading', { name: '스토리지 성능 분석' }).textContent();
            const plotCount = await page.locator('.js-plotly-plot').count();
            return { heading, plotCount };
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.plotCount >= 1, 'Storage dashboard plot count is 0.');
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/04-storage.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'custom-dashboard',
      'Custom dashboard can be selected and rendered.',
      'Custom dashboard heading is missing, or custom charts do not appear.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            const select = page.locator('[data-baseweb="select"]').nth(1);
            await select.click();
            await page.getByRole('option', { name: '사용자 정의 그래프' }).click();
            await page.waitForTimeout(3000);
            const heading = await page.getByRole('heading', { name: '사용자 정의 시각화' }).textContent();
            const plotCount = await page.locator('.js-plotly-plot').count();
            return { heading, plotCount };
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.plotCount >= 1, 'Custom dashboard plot count is 0.');
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/05-custom.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'inspection-upload',
      'AOI inspection log upload creates the export panel and NO range inputs.',
      'AOI upload does not produce two NO inputs, source type AOI, or XLSX export content.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            await page.locator('input[type="file"]').nth(1).setInputFiles(${JSON.stringify(inspectionLogPath)});
            for (let i = 0; i < 60; i += 1) {
              await page.waitForTimeout(1000);
              const bodyText = await page.locator('body').innerText();
              const numberInputs = page.locator('input[type="number"]');
              const numberInputCount = await numberInputs.count();
              if (bodyText.includes('XLSX') && bodyText.includes('감지된 로그 형식: AOI') && numberInputCount >= 2) {
                return {
                  numberInputCount,
                  initialStartNo: await numberInputs.nth(0).inputValue(),
                  initialEndNo: await numberInputs.nth(1).inputValue(),
                  sourceTypeVisible: bodyText.includes('감지된 로그 형식: AOI'),
                };
              }
            }
            throw new Error('Timed out waiting for inspection export panel to appear after AOI upload.');
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(payload.numberInputCount >= 2, `Expected 2 NO inputs, got ${payload.numberInputCount}`);
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/06-inspection-upload.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'inspection-time-filter',
      'Manual time filter shrinks the NO range for the uploaded AOI log.',
      'The two time inputs are missing, Enter does not apply the filter, or the filtered NO range does not shrink.',
      async () => {
        const result = await callTool('browser_run_code', {
          code: `async (page) => {
            const numberInputs = page.locator('input[type="number"]');
            const initialStartNo = await numberInputs.nth(0).inputValue();
            const initialEndNo = await numberInputs.nth(1).inputValue();
            const textInputs = page.locator('input[type="text"]');
            if (await textInputs.count() < 2) {
              throw new Error('Expected at least 2 time filter inputs.');
            }

            await textInputs.nth(0).fill('2026-03-19 00:00:00');
            await textInputs.nth(1).fill('2026-03-19 06:00:00');
            await textInputs.nth(1).press('Enter');

            for (let i = 0; i < 60; i += 1) {
              await page.waitForTimeout(1000);
              const filteredStartNo = await numberInputs.nth(0).inputValue();
              const filteredEndNo = await numberInputs.nth(1).inputValue();
              if (filteredStartNo !== initialStartNo || filteredEndNo !== initialEndNo) {
                return {
                  initialStartNo,
                  initialEndNo,
                  filteredStartNo,
                  filteredEndNo,
                };
              }
            }

            throw new Error('Timed out waiting for filtered NO range values to change.');
          }`,
        });
        const payload = jsonFromToolResult(result);
        assert(Number(payload.filteredStartNo) > Number(payload.initialStartNo), 'Filtered start NO did not increase.');
        assert(Number(payload.filteredEndNo) < Number(payload.initialEndNo), 'Filtered end NO did not decrease.');
        await callTool('browser_take_screenshot', {
          filename: '.artifacts/playwright-prebuild-regression/07-inspection-filter.png',
          type: 'png',
          fullPage: true,
        });
        return payload;
      }
    );

    await runStep(
      'aoi-download-flow',
      'Direct Playwright verifies AOI raw log, parsed CSV, and filtered inspection XLSX downloads.',
      'AOI direct upload/filter fails, any AOI download event does not fire, or a saved AOI file is empty.',
      async () => runDirectAoiDownloadFlow()
    );

    await runStep(
      'spi-download-flow',
      'Direct Playwright verifies SPI upload plus raw ZIP, parsed CSV, and inspection XLSX downloads.',
      'SPI direct upload does not expose Total/Frame values, any SPI download event does not fire, or a saved SPI file is empty.',
      async () => runDirectSpiDownloadFlow()
    );

    await runStep(
      'console-log-export',
      'Console warnings are exported for regression review.',
      'Console export command fails and no browser console artifact is produced.',
      async () => {
        const consoleMessages = await callTool('browser_console_messages', {
          level: 'warning',
          all: true,
          filename: '.artifacts/playwright-prebuild-regression/console-messages.md',
        });
        return {
          consoleSummary: textFromToolResult(consoleMessages),
        };
      }
    );

    await callTool('browser_close', {});

    const summary = {
      ok: true,
      checkedAt: new Date().toISOString(),
      targetUrl,
      systemResourcePath,
      systemProcessPath,
      inspectionLogPath,
      spiCsvPath,
      spiProcessResourcePath,
      downloadDir,
      steps,
      artifacts,
    };
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    try {
      await transport.close();
    } catch (error) {
    }
  }
}

main().catch((error) => {
  const summary = {
    ok: false,
    checkedAt: new Date().toISOString(),
    targetUrl,
    systemResourcePath,
    systemProcessPath,
    inspectionLogPath,
    spiCsvPath,
    spiProcessResourcePath,
    error: error && (error.stack || error.message || String(error)),
    summaryPath,
  };
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
  console.error(JSON.stringify(summary, null, 2));
  process.exit(1);
});
