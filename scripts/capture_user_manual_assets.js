const fs = require('fs');
const path = require('path');

const { chromium } = require(
  path.resolve(__dirname, '..', 'tools', 'playwright-mcp', 'node_modules', 'playwright')
);

const repoRoot = path.resolve(__dirname, '..');
const scenario = process.argv[2] || 'entry-monitoring';
const targetUrl = process.argv[3] || 'http://127.0.0.1:8507';
const defaultSystemResourcePath = path.join(
  repoRoot,
  'bug',
  '20260410-메모리 대시보드 버그',
  'resource_20260410.csv'
);
const defaultSystemProcessPath = path.join(
  repoRoot,
  'bug',
  '20260410-메모리 대시보드 버그',
  'process_20260410.csv'
);
const defaultInspectionLogPath = path.join(repoRoot, 'bug', 'operation_0319_north side grab.log');
const systemResourcePath = process.argv[4] || defaultSystemResourcePath;
const systemProcessPath = process.argv[5] || defaultSystemProcessPath;
const inspectionLogPath = process.argv[6] || defaultInspectionLogPath;

if (!['entry-monitoring', 'dashboards-inspector'].includes(scenario)) {
  console.error(`Unsupported scenario: ${scenario}`);
  process.exit(1);
}

const artifactRoot = path.join(repoRoot, '.artifacts', 'manual-assets', scenario);
const rawDir = path.join(artifactRoot, 'raw');
const approvedDir = path.join(artifactRoot, 'approved');
const summaryPath = path.join(artifactRoot, 'capture-summary.json');
const consoleLogPath = path.join(artifactRoot, 'console-messages.md');

for (const dirPath of [artifactRoot, rawDir, approvedDir]) {
  fs.mkdirSync(dirPath, { recursive: true });
}

const summary = {
  generatedAt: new Date().toISOString(),
  scenario,
  targetUrl,
  inputs: {
    systemResourcePath: toRepoRelativeOrAbsolute(systemResourcePath),
    systemProcessPath: toRepoRelativeOrAbsolute(systemProcessPath),
    inspectionLogPath: toRepoRelativeOrAbsolute(inspectionLogPath),
  },
  approvedFiles: [],
  rawFiles: [],
  consoleMessages: [],
  monitoringResultCaptured: false,
  monitoringResultWarning: null,
  steps: [],
};

function toRepoRelativeOrAbsolute(targetPath) {
  const resolved = path.resolve(targetPath);
  if (resolved.startsWith(repoRoot)) {
    return toRepoRelative(resolved);
  }
  return resolved;
}

function toRepoRelative(targetPath) {
  return path.relative(repoRoot, targetPath).replace(/\\/g, '/');
}

function recordStep(name, payload) {
  summary.steps.push({ name, ...payload });
}

function roundClip(box) {
  return {
    x: Math.max(0, Math.floor(box.x)),
    y: Math.max(0, Math.floor(box.y)),
    width: Math.max(1, Math.ceil(box.width)),
    height: Math.max(1, Math.ceil(box.height)),
  };
}

async function takeRaw(page, fileName, options) {
  const outputPath = path.join(rawDir, fileName);
  await page.screenshot({ path: outputPath, ...options });
  summary.rawFiles.push(toRepoRelative(outputPath));
  return outputPath;
}

async function takeApproved(page, fileName, options) {
  const outputPath = path.join(approvedDir, fileName);
  await page.screenshot({ path: outputPath, ...options });
  summary.approvedFiles.push(toRepoRelative(outputPath));
  return outputPath;
}

async function waitForMainUi(page) {
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByRole('heading', { name: '시스템 자원 대시보드' }).waitFor({ timeout: 30000 });
  await page.getByRole('button', { name: '모니터링 시작' }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(2500);
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function getSidebarTopClip(page) {
  const sidebar = page.locator('section[data-testid="stSidebar"]').first();
  await sidebar.waitFor({ timeout: 15000 });

  const sidebarBox = await sidebar.boundingBox();
  if (!sidebarBox) {
    throw new Error('Could not resolve sidebar bounding box.');
  }

  const logHeader = page.getByText('로그 파일 선택', { exact: true });
  const logHeaderBox = await logHeader.boundingBox().catch(() => null);

  const desiredHeight = logHeaderBox
    ? Math.min(sidebarBox.height, logHeaderBox.y + logHeaderBox.height + 28 - sidebarBox.y)
    : Math.min(sidebarBox.height, 560);

  return roundClip({
    x: sidebarBox.x,
    y: sidebarBox.y,
    width: sidebarBox.width,
    height: desiredHeight,
  });
}

async function getHomeOverviewClip(page) {
  const viewportSize = page.viewportSize();
  if (!viewportSize) {
    throw new Error('Could not resolve viewport size.');
  }

  return roundClip({
    x: 0,
    y: 0,
    width: viewportSize.width,
    height: Math.min(780, viewportSize.height),
  });
}

async function uploadSystemLogs(page) {
  await page.locator('input[type="file"]').nth(0).setInputFiles([systemResourcePath, systemProcessPath]);
  for (let i = 0; i < 50; i += 1) {
    await page.waitForTimeout(1000);
    const payload = await page.evaluate(() => {
      const plotCount = document.querySelectorAll('.js-plotly-plot').length;
      const bodyText = document.body.innerText || '';
      const hasSystemRows = bodyText.includes('시스템 모니터 행');
      return {
        plotCount,
        hasSystemRows,
      };
    });
    if (payload.plotCount > 0 && payload.hasSystemRows) {
      return payload;
    }
  }
  throw new Error('Timed out waiting for system CSV dashboards to render.');
}

async function uploadInspectionLog(page) {
  await page.locator('input[type="file"]').nth(1).setInputFiles(inspectionLogPath);
  for (let i = 0; i < 80; i += 1) {
    await page.waitForTimeout(1000);
    const bodyText = await page.locator('body').innerText();
    if (bodyText.includes('업로드한 파일') && bodyText.includes('인스펙터 이벤트')) {
      return { uploadMessageVisible: true };
    }
    if (bodyText.includes('검사 결과 XLSX 내보내기') && bodyText.includes('총 검사 수')) {
      return { exportPanelVisible: true };
    }
  }
  throw new Error('Timed out waiting for AOI / 인스펙터 로그 업로드 결과 to appear.');
}

async function selectDashboard(page, label, heading) {
  const dashboardSelect = page.locator('[data-baseweb="select"]').nth(1);
  await dashboardSelect.click();
  await page.getByRole('option', { name: label }).click();
  if (heading) {
    await page.getByRole('heading', { name: heading }).waitFor({ timeout: 20000 });
  }
  await page.waitForTimeout(2500);
}

async function getMainDashboardClip(page, headingText) {
  const heading = page.getByRole('heading', { name: headingText });
  await heading.waitFor({ timeout: 20000 });
  await heading.evaluate((node) => {
    node.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'instant' });
  });
  await page.waitForTimeout(1000);

  const headingBox = await heading.boundingBox();
  const viewportSize = page.viewportSize();
  if (!headingBox || !viewportSize) {
    throw new Error(`Could not resolve main dashboard clip for ${headingText}.`);
  }

  return roundClip({
    x: 280,
    y: Math.max(0, headingBox.y - 110),
    width: Math.max(100, viewportSize.width - 300),
    height: Math.min(920, viewportSize.height - Math.max(0, headingBox.y - 110)),
  });
}

async function getSidebarSectionClip(page, headerText, fallbackHeight = 520) {
  const sidebar = page.locator('section[data-testid="stSidebar"]').first();
  await sidebar.waitFor({ timeout: 15000 });
  const header = page.getByText(headerText, { exact: true });
  await header.evaluate((node) => {
    node.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'instant' });
  });
  await page.waitForTimeout(1000);

  const sidebarBox = await sidebar.boundingBox();
  const headerBox = await header.boundingBox();
  if (!sidebarBox || !headerBox) {
    throw new Error(`Could not resolve sidebar clip for ${headerText}.`);
  }

  return roundClip({
    x: sidebarBox.x,
    y: Math.max(sidebarBox.y, headerBox.y - 24),
    width: sidebarBox.width,
    height: Math.min(fallbackHeight, sidebarBox.y + sidebarBox.height - Math.max(sidebarBox.y, headerBox.y - 24)),
  });
}

async function getExportPanelClip(page) {
  const header = page.getByRole('heading', { name: '검사 결과 XLSX 내보내기' });
  await header.waitFor({ timeout: 20000 });
  await header.evaluate((node) => {
    node.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'instant' });
  });
  await page.waitForTimeout(1000);

  const headerBox = await header.boundingBox();
  const viewportSize = page.viewportSize();
  if (!headerBox || !viewportSize) {
    throw new Error('Could not resolve export panel clip.');
  }

  return roundClip({
    x: 260,
    y: Math.max(0, headerBox.y - 40),
    width: Math.max(100, viewportSize.width - 300),
    height: Math.min(980, viewportSize.height - Math.max(0, headerBox.y - 40)),
  });
}

async function getExportPreviewClip(page) {
  const downloadButton = page.getByRole('button', { name: '검사 결과 XLSX 다운로드' });
  await downloadButton.waitFor({ timeout: 20000 });
  await downloadButton.evaluate((node) => {
    node.scrollIntoView({ block: 'end', inline: 'nearest', behavior: 'instant' });
  });
  await page.waitForTimeout(1000);

  const buttonBox = await downloadButton.boundingBox();
  const viewportSize = page.viewportSize();
  if (!buttonBox || !viewportSize) {
    throw new Error('Could not resolve export preview clip.');
  }

  const topY = Math.max(0, buttonBox.y - 760);
  return roundClip({
    x: 260,
    y: topY,
    width: Math.max(100, viewportSize.width - 300),
    height: Math.min(980, viewportSize.height - topY),
  });
}

async function getTimeFilterClip(page) {
  const sidebar = page.locator('section[data-testid="stSidebar"]').first();
  const startInput = page.getByLabel('시작 시간');
  const endInput = page.getByLabel('종료 시간');
  await sidebar.waitFor({ timeout: 15000 });
  await startInput.waitFor({ timeout: 20000 });
  await startInput.evaluate((node) => {
    node.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'instant' });
  });
  await page.waitForTimeout(1000);

  const sidebarBox = await sidebar.boundingBox();
  const startBox = await startInput.boundingBox();
  const endBox = await endInput.boundingBox();
  if (!sidebarBox || !startBox || !endBox) {
    throw new Error('Could not resolve time filter clip.');
  }

  const topY = Math.max(sidebarBox.y, Math.min(startBox.y, endBox.y) - 180);
  return roundClip({
    x: sidebarBox.x,
    y: topY,
    width: sidebarBox.width,
    height: Math.min(360, sidebarBox.y + sidebarBox.height - topY),
  });
}

async function getChartToolbarClip(page) {
  const chart = page.locator('.js-plotly-plot').first();
  await chart.waitFor({ timeout: 20000 });
  const chartBox = await chart.boundingBox();
  if (!chartBox) {
    throw new Error('Could not resolve chart bounding box.');
  }

  await page.mouse.move(chartBox.x + chartBox.width - 20, chartBox.y + 20);
  await page.waitForTimeout(900);

  return roundClip({
    x: Math.max(0, chartBox.x + chartBox.width - 280),
    y: Math.max(0, chartBox.y - 6),
    width: 260,
    height: 90,
  });
}

function writeConsoleLog() {
  const lines = ['# Browser Console Messages', ''];
  if (!summary.consoleMessages.length) {
    lines.push('- No console messages captured.');
  } else {
    for (const entry of summary.consoleMessages) {
      lines.push(`- [${entry.type}] ${entry.text}`);
    }
  }
  fs.writeFileSync(consoleLogPath, `${lines.join('\n')}\n`, 'utf-8');
}

async function main() {
  let browser;
  let context;
  let page;
  try {
    browser = await chromium.launch({
      channel: 'msedge',
      headless: true,
    });

    context = await browser.newContext({
      viewport: { width: 1440, height: 1220 },
      deviceScaleFactor: 1,
    });

    page = await context.newPage();
    page.on('console', (message) => {
      summary.consoleMessages.push({
        type: message.type(),
        text: message.text(),
      });
    });

    await waitForMainUi(page);
    recordStep('page-ready', {
      ok: true,
      stdout: {
        titleVisible: true,
        targetUrl,
      },
    });

    if (scenario === 'entry-monitoring') {
      await takeRaw(page, '01-entry-home-full.png', { fullPage: true });
      await takeRaw(page, '02-entry-home-viewport.png', { fullPage: false });
      const homeOverviewClip = await getHomeOverviewClip(page);
      await takeApproved(page, 'entry-home-overview.png', { clip: homeOverviewClip });
      recordStep('entry-home-overview', {
        ok: true,
        stdout: {
          approved: 'entry-home-overview.png',
          clip: homeOverviewClip,
        },
      });

      const sidebarClip = await getSidebarTopClip(page);
      await takeRaw(page, '03-entry-control-panel-full.png', { clip: sidebarClip });
      await takeApproved(page, 'entry-control-panel-start.png', { clip: sidebarClip });
      recordStep('entry-control-panel-start', {
        ok: true,
        stdout: {
          approved: 'entry-control-panel-start.png',
          clip: sidebarClip,
        },
      });

      let monitoringResultError = null;
      try {
        await page.getByRole('button', { name: '모니터링 시작' }).click();
        await page.getByText('Python 모니터를 시작했습니다.', { exact: true }).waitFor({ timeout: 12000 });
        await page.getByText('명령 프롬프트 창이 열리며, 창을 닫으면 모니터링이 종료됩니다.', { exact: true }).waitFor({
          timeout: 12000,
        });
        await page.waitForTimeout(1200);

        const resultClip = await getSidebarTopClip(page);
        await takeRaw(page, '04-entry-monitoring-result-full.png', { clip: resultClip });
        await takeApproved(page, 'entry-monitoring-result.png', { clip: resultClip });

        summary.monitoringResultCaptured = true;
        recordStep('entry-monitoring-result', {
          ok: true,
          stdout: {
            approved: 'entry-monitoring-result.png',
            clip: resultClip,
          },
        });
      } catch (error) {
        monitoringResultError = error;
        summary.monitoringResultWarning = error.message || String(error);
        await takeRaw(page, '04-entry-monitoring-result-fallback.png', { fullPage: false });
        recordStep('entry-monitoring-result', {
          ok: false,
          warning: summary.monitoringResultWarning,
        });
      }

      if (monitoringResultError) {
        process.exitCode = 0;
      }
    }

    if (scenario === 'dashboards-inspector') {
      if (!fs.existsSync(systemResourcePath) || !fs.existsSync(systemProcessPath) || !fs.existsSync(inspectionLogPath)) {
        throw new Error('One or more default input files for dashboards-inspector scenario do not exist.');
      }

      const systemUploadPayload = await uploadSystemLogs(page);
      recordStep('system-log-upload', {
        ok: true,
        stdout: systemUploadPayload,
      });

      const systemSidebarClip = await getSidebarSectionClip(page, '로그 파일 선택', 760);
      await takeRaw(page, '00-system-log-selection-full.png', { clip: systemSidebarClip });
      await takeApproved(page, 'system-log-selection.png', { clip: systemSidebarClip });
      recordStep('system-log-selection', {
        ok: true,
        stdout: {
          approved: 'system-log-selection.png',
          clip: systemSidebarClip,
        },
      });

      const timeFilterClip = await getTimeFilterClip(page);
      await takeRaw(page, '00-time-filter-full.png', { clip: timeFilterClip });
      await takeApproved(page, 'time-range-filter.png', { clip: timeFilterClip });
      recordStep('time-range-filter', {
        ok: true,
        stdout: {
          approved: 'time-range-filter.png',
          clip: timeFilterClip,
        },
      });

      await takeRaw(page, '01-cpu-dashboard-full.png', { fullPage: false });
      const cpuClip = await getMainDashboardClip(page, 'CPU 성능 및 온도');
      await takeApproved(page, 'cpu-dashboard-overview.png', { clip: cpuClip });
      recordStep('cpu-dashboard', {
        ok: true,
        stdout: {
          approved: 'cpu-dashboard-overview.png',
          clip: cpuClip,
        },
      });

      const toolbarClip = await getChartToolbarClip(page);
      await takeRaw(page, '01-cpu-chart-toolbar-full.png', { clip: toolbarClip });
      await takeApproved(page, 'chart-toolbar.png', { clip: toolbarClip });
      recordStep('chart-toolbar', {
        ok: true,
        stdout: {
          approved: 'chart-toolbar.png',
          clip: toolbarClip,
        },
      });

      const inspectionUploadPayload = await uploadInspectionLog(page);
      recordStep('inspection-log-upload', {
        ok: true,
        stdout: inspectionUploadPayload,
      });

      const inspectorSidebarClip = await getSidebarSectionClip(page, 'AOI / 인스펙터 로그', 620);
      await takeRaw(page, '02-inspector-sidebar-full.png', { clip: inspectorSidebarClip });
      await takeApproved(page, 'inspector-log-upload.png', { clip: inspectorSidebarClip });
      recordStep('inspector-log-upload-panel', {
        ok: true,
        stdout: {
          approved: 'inspector-log-upload.png',
          clip: inspectorSidebarClip,
        },
      });

      await selectDashboard(page, '메모리 + 인스펙터 대시보드', '메모리 및 인스펙터 분석');
      const memoryClip = await getMainDashboardClip(page, '메모리 및 인스펙터 분석');
      await takeRaw(page, '03-memory-dashboard-full.png', { clip: memoryClip });
      await takeApproved(page, 'memory-inspector-dashboard.png', { clip: memoryClip });
      recordStep('memory-inspector-dashboard', {
        ok: true,
        stdout: {
          approved: 'memory-inspector-dashboard.png',
          clip: memoryClip,
        },
      });

      const exportClip = await getExportPanelClip(page);
      await takeRaw(page, '04-inspection-export-full.png', { clip: exportClip });
      await takeApproved(page, 'inspection-export-panel.png', { clip: exportClip });
      recordStep('inspection-export-panel', {
        ok: true,
        stdout: {
          approved: 'inspection-export-panel.png',
          clip: exportClip,
        },
      });

      const exportPreviewClip = await getExportPreviewClip(page);
      await takeRaw(page, '05-inspection-export-preview-full.png', { clip: exportPreviewClip });
      await takeApproved(page, 'inspection-export-preview.png', { clip: exportPreviewClip });
      recordStep('inspection-export-preview', {
        ok: true,
        stdout: {
          approved: 'inspection-export-preview.png',
          clip: exportPreviewClip,
        },
      });

      await selectDashboard(page, '스토리지 대시보드', '스토리지 성능 분석');
      const storageClip = await getMainDashboardClip(page, '스토리지 성능 분석');
      await takeRaw(page, '06-storage-dashboard-full.png', { clip: storageClip });
      await takeApproved(page, 'storage-dashboard-overview.png', { clip: storageClip });
      recordStep('storage-dashboard', {
        ok: true,
        stdout: {
          approved: 'storage-dashboard-overview.png',
          clip: storageClip,
        },
      });

      await selectDashboard(page, '사용자 정의 그래프', '사용자 정의 시각화');
      const customClip = await getMainDashboardClip(page, '사용자 정의 시각화');
      await takeRaw(page, '07-custom-dashboard-full.png', { clip: customClip });
      await takeApproved(page, 'custom-dashboard-overview.png', { clip: customClip });
      recordStep('custom-dashboard', {
        ok: true,
        stdout: {
          approved: 'custom-dashboard-overview.png',
          clip: customClip,
        },
      });
    }

    writeConsoleLog();
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf-8');

    console.log(JSON.stringify(summary, null, 2));
  } catch (error) {
    writeConsoleLog();
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf-8');
    console.error(error && (error.stack || error.message || String(error)));
    process.exitCode = 1;
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
    if (context) {
      await context.close().catch(() => {});
    }
    if (browser) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      await browser.close();
    }
  }
}

main();
