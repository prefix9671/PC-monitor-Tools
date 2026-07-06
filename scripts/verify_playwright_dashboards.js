const fs = require('fs');
const path = require('path');
const mcp = require(path.resolve(__dirname, '..', 'tools', 'playwright-mcp', 'node_modules', 'playwright-core', 'lib', 'mcpBundle'));

const repoRoot = path.resolve(__dirname, '..');
const artifactDir = path.join(repoRoot, '.artifacts', 'playwright-dashboard-test');
const outputDir = path.join(artifactDir, 'mcp-session');
const summaryPath = path.join(artifactDir, 'dashboard-summary.json');
const targetUrl = process.argv[2] || 'http://127.0.0.1:8502';

fs.mkdirSync(outputDir, { recursive: true });

function textFromToolResult(result) {
  return (result.content || [])
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('\n');
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function main() {
  const client = new mcp.Client({ name: 'pc-monitor-playwright-check', version: '0.1' });
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

  const results = [];
  const callTool = async (name, args = {}) => {
    const result = await client.callTool({ name, arguments: args });
    if (result.isError) {
      throw new Error(`${name} failed: ${textFromToolResult(result)}`);
    }
    return result;
  };

  try {
    await client.connect(transport);

    await callTool('browser_navigate', { url: targetUrl });
    const home = await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByRole('heading', { name: '시스템 자원 대시보드' }).waitFor({ timeout: 60000 });
        await page.getByText('시스템 모니터 행').waitFor({ timeout: 60000 });
        return {
          title: await page.title(),
          systemRowsLoaded: await page.getByText('시스템 모니터 행').first().textContent(),
          plotCount: await page.locator('.js-plotly-plot').count(),
        };
      }`,
    });
    results.push({ dashboard: 'Home', details: textFromToolResult(home) });
    await callTool('browser_take_screenshot', {
      filename: '.artifacts/playwright-dashboard-test/01-home.png',
      type: 'png',
      fullPage: true,
    });

    const cpu = await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByRole('heading', { name: 'CPU 성능 및 온도' }).waitFor({ timeout: 60000 });
        return {
          heading: await page.getByRole('heading', { name: 'CPU 성능 및 온도' }).textContent(),
          plotCount: await page.locator('.js-plotly-plot').count(),
          hasCpuCaption: await page.getByText('CPU 온도는 5초 동안 수집된 최고값입니다.').count(),
        };
      }`,
    });
    const cpuText = textFromToolResult(cpu);
    assert(cpuText.includes('CPU 성능 및 온도'), 'CPU dashboard heading not found');
    results.push({ dashboard: 'CPU', details: cpuText });
    await callTool('browser_take_screenshot', {
      filename: '.artifacts/playwright-dashboard-test/02-cpu.png',
      type: 'png',
      fullPage: true,
    });

    const memory = await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByText('대시보드 보기 선택').waitFor({ timeout: 60000 });
        const select = page.locator('[data-baseweb="select"]').nth(1);
        await select.click();
        await page.getByRole('option', { name: '메모리 + 인스펙터 대시보드' }).click();
        await page.getByRole('heading', { name: '메모리 및 AOI/SPI 분석' }).waitFor({ timeout: 60000 });
        return {
          heading: await page.getByRole('heading', { name: '메모리 및 AOI/SPI 분석' }).textContent(),
          plotCount: await page.locator('.js-plotly-plot').count(),
          captionCount: await page.getByText('현재 표시되는 메모리 그래프와 프로세스 사용량은 5초 단위 집계값').count(),
        };
      }`,
    });
    const memoryText = textFromToolResult(memory);
    assert(memoryText.includes('메모리 및 AOI/SPI 분석'), 'Memory dashboard heading not found');
    results.push({ dashboard: 'Memory+Inspector', details: memoryText });
    await callTool('browser_take_screenshot', {
      filename: '.artifacts/playwright-dashboard-test/03-memory.png',
      type: 'png',
      fullPage: true,
    });

    const storage = await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByText('대시보드 보기 선택').waitFor({ timeout: 60000 });
        const select = page.locator('[data-baseweb="select"]').nth(1);
        await select.click();
        await page.getByRole('option', { name: '스토리지 대시보드' }).click();
        await page.getByRole('heading', { name: '스토리지 성능 분석' }).waitFor({ timeout: 60000 });
        return {
          heading: await page.getByRole('heading', { name: '스토리지 성능 분석' }).textContent(),
          plotCount: await page.locator('.js-plotly-plot').count(),
          qualityLabelVisible: await page.getByText('차트 품질').count(),
        };
      }`,
    });
    const storageText = textFromToolResult(storage);
    assert(storageText.includes('스토리지 성능 분석'), 'Storage dashboard heading not found');
    results.push({ dashboard: 'Storage', details: storageText });
    await callTool('browser_take_screenshot', {
      filename: '.artifacts/playwright-dashboard-test/04-storage.png',
      type: 'png',
      fullPage: true,
    });

    const custom = await callTool('browser_run_code', {
      code: `async (page) => {
        await page.getByText('대시보드 보기 선택').waitFor({ timeout: 60000 });
        const select = page.locator('[data-baseweb="select"]').nth(1);
        await select.click();
        await page.getByRole('option', { name: '사용자 정의 그래프' }).click();
        await page.getByRole('heading', { name: '사용자 정의 시각화' }).waitFor({ timeout: 60000 });
        await page.getByText('엑셀(.xlsx) 다운로드').waitFor({ timeout: 60000 });
        return {
          heading: await page.getByRole('heading', { name: '사용자 정의 시각화' }).textContent(),
          excelButtonVisible: await page.getByText('엑셀(.xlsx) 다운로드').count(),
          plotCount: await page.locator('.js-plotly-plot').count(),
        };
      }`,
    });
    const customText = textFromToolResult(custom);
    assert(customText.includes('사용자 정의 시각화'), 'Custom dashboard heading not found');
    results.push({ dashboard: 'Custom', details: customText });
    await callTool('browser_take_screenshot', {
      filename: '.artifacts/playwright-dashboard-test/05-custom.png',
      type: 'png',
      fullPage: true,
    });

    const consoleMessages = await callTool('browser_console_messages', {
      level: 'warning',
      all: true,
      filename: '.artifacts/playwright-dashboard-test/console-messages.md',
    });
    results.push({ dashboard: 'Console', details: textFromToolResult(consoleMessages) });

    await callTool('browser_close', {});

    const summary = {
      ok: true,
      checkedAt: new Date().toISOString(),
      targetUrl,
      results,
      artifacts: [
        '.artifacts/playwright-dashboard-test/01-home.png',
        '.artifacts/playwright-dashboard-test/02-cpu.png',
        '.artifacts/playwright-dashboard-test/03-memory.png',
        '.artifacts/playwright-dashboard-test/04-storage.png',
        '.artifacts/playwright-dashboard-test/05-custom.png',
        '.artifacts/playwright-dashboard-test/console-messages.md',
      ],
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
    error: error && (error.stack || error.message || String(error)),
  };
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
  console.error(JSON.stringify(summary, null, 2));
  process.exit(1);
});
