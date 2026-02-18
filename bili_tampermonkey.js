// ==UserScript==
// @name         Bilibili AI Summary Assistant - MP3_TO_TXT
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Call local MP3_TO_TXT service to summarize Bilibili videos
// @author       You
// @match        https://www.bilibili.com/video/BV*
// @grant        GM_xmlhttpRequest
// @grant        GM_registerMenuCommand
// @connect      localhost
// ==/UserScript==

(function() {
    'use strict';

    const API_URL = "http://localhost:8000";

    function getBvId() {
        // ... (existing code)
        const path = window.location.pathname;
        const match = path.match(/(BV\w+)/);
        return match ? match[1] : null;
    }

    // Creating UI
    function createUI() {
        let container = document.getElementById('ai-summary-control');
        if (container) return container;

        container = document.createElement('div');
        container.id = 'ai-summary-control';
        container.style.cssText = `
            position: fixed;
            top: 150px;
            right: 0;
            background: #fff;
            border: 1px solid #ddd;
            border-right: none;
            border-radius: 8px 0 0 8px;
            padding: 10px;
            z-index: 9999;
            box-shadow: -2px 0 8px rgba(0,0,0,0.1);
            width: 280px;
            transition: transform 0.3s;
        `;

        // Toggle button
        const toggleBtn = document.createElement('div');
        toggleBtn.innerText = "🤖 AI";
        toggleBtn.style.cssText = `
            position: absolute;
            left: -30px;
            top: 10px;
            width: 30px;
            height: 30px;
            background: #00aeec;
            color: white;
            text-align: center;
            line-height: 30px;
            border-radius: 4px 0 0 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        toggleBtn.onclick = () => {
            const currentRight = parseInt(container.style.right || '0');
            container.style.right = currentRight === 0 ? '-280px' : '0';
        };
        container.appendChild(toggleBtn);
        
        // 1. Preset Selector
        const label1 = document.createElement('div');
        label1.innerText = "选择模式:";
        label1.style.fontWeight = "bold";
        label1.style.marginBottom = "5px";
        container.appendChild(label1);

        const select = document.createElement('select');
        select.id = 'ai-preset-select';
        select.style.width = "100%";
        select.style.marginBottom = "10px";
        select.style.padding = "5px";
        container.appendChild(select);

        // Fetch presets with fallback
        GM_xmlhttpRequest({
            method: "GET",
            url: API_URL + "/presets",
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        const presets = JSON.parse(response.responseText);
                        fillPresets(presets);
                    } catch (e) {
                        console.warn("Preset parse failed, using fallback");
                        fillFallback();
                    }
                } else {
                    fillFallback();
                }
            },
            onerror: function(e) {
                console.warn("Preset load failed (backend likely down), using fallback");
                fillFallback();
            }
        });

        function fillPresets(list) {
            select.innerHTML = "";
            list.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.key;
                opt.innerText = p.label;
                select.appendChild(opt);
            });
            select.value = "bilibili_summary";
        }

        function fillFallback() {
            const fallback = [
                {key: "bilibili_summary", label: "📄 视频总结 (Fallback)"},
                {key: "meeting_summary", label: "📝 会议纪要"},
                {key: "translation", label: "🌏 全文翻译"}
            ];
            fillPresets(fallback);
        }

        // 2. Custom Prompt
        const label2 = document.createElement('div');
        label2.innerText = "自定义提示词 (可选):";
        label2.style.fontWeight = "bold";
        label2.style.marginBottom = "5px";
        label2.style.marginTop = "10px";
        container.appendChild(label2);

        const textarea = document.createElement('textarea');
        textarea.id = 'ai-custom-prompt';
        textarea.style.width = "100%";
        textarea.style.height = "80px";
        textarea.placeholder = "在此输入将覆盖预设...";
        textarea.style.marginBottom = "10px";
        container.appendChild(textarea);

        // 3. Action Button
        const btn = document.createElement('button');
        btn.innerText = "生成摘要/翻译";
        btn.style.cssText = `
            width: 100%;
            background: #00aeec;
            color: white;
            border: none;
            padding: 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        btn.onclick = callLocalService;
        container.appendChild(btn);

        // 4. Status Area
        const statusDiv = document.createElement('div');
        statusDiv.id = 'ai-status-msg';
        statusDiv.style.marginTop = "10px";
        statusDiv.style.fontSize = "12px";
        statusDiv.style.color = "#666";
        container.appendChild(statusDiv);

        document.body.appendChild(container);
    }

    function callLocalService() {
        const bvId = getBvId();
        if (!bvId) {
            alert("未找到 BV 号!");
            return;
        }

        const preset = document.getElementById('ai-preset-select').value;
        const customPrompt = document.getElementById('ai-custom-prompt').value;
        const statusDiv = document.getElementById('ai-status-msg');

        statusDiv.innerText = "🚀 提交任务中...";
        statusDiv.style.color = "blue";

        GM_xmlhttpRequest({
            method: "POST",
            url: API_URL + "/process",
            headers: {
                "Content-Type": "application/json"
            },
            data: JSON.stringify({
                source: bvId,
                skip_download: false,
                preset_name: preset,
                custom_prompt: customPrompt
            }),
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        const result = JSON.parse(response.responseText);
                        console.log("[AI Summary] Task queued:", result);
                        if (result.task_id) {
                            pollStatus(result.task_id, statusDiv);
                        } else {
                            statusDiv.innerText = "❌ 任务提交响应异常";
                            statusDiv.style.color = "red";
                        }
                    } catch (e) {
                        console.error("[AI Summary] Error parsing response:", e);
                        statusDiv.innerText = "❌ 提交解析错误";
                        statusDiv.style.color = "red";
                    }
                } else {
                    console.error("[AI Summary] Failed:", response.responseText);
                    statusDiv.innerText = "❌ 提交失败: " + response.status;
                    statusDiv.style.color = "red";
                }
            },
            onerror: function(err) {
                console.error("[AI Summary] Request error:", err);
                statusDiv.innerText = "❌ 连接失败 (检查本地服务)";
                statusDiv.style.color = "red";
            }
        });
    }

    function pollStatus(taskId, statusDiv) {
        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            GM_xmlhttpRequest({
                method: "GET",
                url: API_URL + "/status/" + taskId,
                onload: function(response) {
                    if (response.status === 200) {
                        const task = JSON.parse(response.responseText);
                        console.log(`[AI Summary] Poll status: ${task.status}`, task);
                        
                        if (task.status === "succeeded") {
                            clearInterval(interval);
                            statusDiv.innerText = "✅ 处理完成!";
                            statusDiv.style.color = "green";
                            if (task.result && task.result.summary) {
                                showSummary(task.result.summary);
                            }
                        } else if (task.status === "failed") {
                            clearInterval(interval);
                            statusDiv.innerText = "❌ 任务失败: " + task.error;
                            statusDiv.style.color = "red";
                        } else {
                            // processing or queued
                            statusDiv.innerText = `⏳ 处理中... (${task.status}) ${attempts}s`;
                            statusDiv.style.color = "blue";
                        }
                    } else {
                        // Network error allowed to retry a few times?
                        statusDiv.innerText = "⚠️ 状态查询异常: " + response.status;
                    }
                },
                onerror: function() {
                    statusDiv.innerText = "⚠️ 网络连接闪断...";
                }
            });
        }, 1000); // Poll every 1 second
    }

    // Simplified showSummary (since we have the UI panel now, maybe just popup a modal or expand?)
    function showSummary(summaryText) {
        // ... reuse existing logic or create a large modal
        // Let's create a modal for the result
        let modal = document.getElementById('ai-result-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'ai-result-modal';
            modal.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 600px;
                max-width: 90%;
                max-height: 80vh;
                background: white;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
                z-index: 10000;
                padding: 20px;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
            `;
            
            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.marginBottom = '15px';
            header.innerHTML = '<h3>📝 AI 生成结果</h3><button id="ai-modal-close" style="cursor:pointer;border:none;background:none;font-size:20px;">✖</button>';
            modal.appendChild(header);

            const content = document.createElement('textarea');
            content.id = 'ai-result-text';
            content.style.cssText = `
                width: 100%;
                flex: 1;
                min-height: 300px;
                padding: 10px;
                border: 1px solid #ccc;
                font-family: monospace;
                resize: vertical;
            `;
            modal.appendChild(content);
            
            document.body.appendChild(modal);
            document.getElementById('ai-modal-close').onclick = () => modal.style.display = 'none';
        }

        const modalEl = document.getElementById('ai-result-modal');
        modalEl.style.display = 'flex';
        document.getElementById('ai-result-text').value = summaryText;
    }

    // Initialize
    setTimeout(createUI, 2000); // Verify wait for page load
    GM_registerMenuCommand("打开 AI 助手", createUI);
})();