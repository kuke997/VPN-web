async function loadNodes() {
  // 显示加载状态
  const loading = document.getElementById('loading');
  if (loading) {
    loading.style.display = 'block';
    const loadingText = loading.querySelector('p');
    if (loadingText) {
      loadingText.textContent = translations[currentLang]['nodes.loading'] || '正在加载节点数据，请稍候...';
    }
  }
  
  try {
    // 添加时间戳防止缓存
    const timestamp = new Date().getTime();
    const res = await fetch(`/nodes.json?t=${timestamp}`, { 
      cache: 'no-store',
      credentials: 'same-origin'
    });
    
    if (!res.ok) {
      throw new Error(translations[currentLang]['nodes.load_failed'] || '加载节点数据失败');
    }
    
    // 获取响应文本
    const text = await res.text();
    
    // 尝试解析JSON
    const data = JSON.parse(text);
    
    return data;
  } catch (error) {
    console.error('加载 nodes.json 出错：', error);
    
    // 更新加载状态为错误信息
    if (loading) {
      loading.innerHTML = `
        <div class="error-message">
          <p>⚠️ ${translations[currentLang]['nodes.load_failed_title'] || '加载节点数据失败'}</p>
          <p>${error.message}</p>
          <p>${translations[currentLang]['nodes.load_failed_message'] || '请刷新页面重试或稍后再访问'}</p>
          <button onclick="location.reload()" style="margin-top:10px; background:#007bff; color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">
            ${translations[currentLang]['nodes.refresh'] || '刷新页面'}
          </button>
        </div>
      `;
    }
    
    return [];
  }
}

function getProtocolType(type) {
  const key = `protocol.${type}`;
  return translations[currentLang][key] || type;
}

function getStatusText(status, latency) {
  if (status) {
    return `${translations[currentLang]['nodes.latency'] || '延迟'}: ${latency}ms`;
  }
  return translations[currentLang]['nodes.inactive'] || '已失效';
}

// 全局排序状态
let currentSort = { field: 'latency', ascending: true };

function sortNodes(nodes, field, ascending) {
    return nodes.sort((a, b) => {
        let valueA, valueB;
        
        if (field === 'latency') {
            valueA = a.latency || 9999;
            valueB = b.latency || 9999;
        } else if (field === 'name') {
            valueA = a.name || '';
            valueB = b.name || '';
        } else if (field === 'type') {
            valueA = a.type || '';
            valueB = b.type || '';
        }
        
        if (valueA === valueB) return 0;
        if (ascending) {
            return valueA < valueB ? -1 : 1;
        } else {
            return valueA > valueB ? -1 : 1;
        }
    });
}

function createServerTable(nodes) {
    // 按当前排序状态排序
    nodes = sortNodes(nodes, currentSort.field, currentSort.ascending);
    
    const table = document.createElement('table');
    table.className = 'server-table';
    
    // 创建表头
    const thead = document.createElement('thead');
    thead.innerHTML = `
    <tr>
        <th class="sortable" onclick="sortTable('name')">
            ${translations[currentLang]['nodes.name'] || '名称'}
            <span id="name-sort-icon">↕️</span>
        </th>
        <th class="sortable" onclick="sortTable('type')">
            ${translations[currentLang]['nodes.type'] || '类型'}
            <span id="type-sort-icon">↕️</span>
        </th>
        <th class="sortable" onclick="sortTable('latency')">
            ${translations[currentLang]['nodes.status'] || '状态'}
            <span id="latency-sort-icon">${currentSort.field === 'latency' ? (currentSort.ascending ? '⬆️' : '⬇️') : '↕️'}</span>
        </th>
        <th>${translations[currentLang]['nodes.operation'] || '操作'}</th>
    </tr>
    `;
    table.appendChild(thead);
    
    // 创建表格主体
    const tbody = document.createElement('tbody');
    
    nodes.forEach(node => {
        const row = document.createElement('tr');
        
        // 名称列
        const nameCell = document.createElement('td');
        nameCell.textContent = node.name || translations[currentLang]['nodes.unnamed'] || '未知节点';
        row.appendChild(nameCell);
        
        // 类型列
        const typeCell = document.createElement('td');
        const protocolType = getProtocolType(node.type || '');
        typeCell.textContent = protocolType;
        row.appendChild(typeCell);
        
        // 状态列
        const statusCell = document.createElement('td');
        const isActive = node.latency && node.latency < 500;
        statusCell.innerHTML = `
        <span class="status-indicator ${isActive ? 'active' : 'inactive'}"></span>
        <span class="status-text">${getStatusText(isActive, node.latency)}</span>
        `;
        row.appendChild(statusCell);
        
        // 操作列
        const actionCell = document.createElement('td');
        
        // 根据节点类型创建不同的操作
        if (node.clash_config) {
            // 配置下载按钮
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'download-link';
            downloadBtn.textContent = translations[currentLang]['nodes.download'] || '下载配置';
            downloadBtn.onclick = () => {
                try {
                    // 创建有意义的文件名
                    let fileName = node.name.replace(/[^a-z0-9]/gi, '_') || 'vpn_config';
                    fileName = fileName.substring(0, 30); // 限制文件名长度
                    
                    // 根据协议类型添加扩展名
                    if (node.type === 'vmess' || node.type === 'trojan' || node.type === 'ss') {
                        fileName += '.yaml';
                    } else {
                        fileName += '.txt';
                    }
                    
                    // 创建配置内容
                    const configContent = yaml.dump(node.clash_config, {lineWidth: -1});
                    
                    const blob = new Blob([configContent], { type: 'text/yaml' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = fileName;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } catch (e) {
                    console.error('下载失败:', e);
                    alert(`${translations[currentLang]['nodes.download_failed'] || '下载失败'}: ${e.message}`);
                }
            };
            actionCell.appendChild(downloadBtn);
        } else if (node.server && node.port) {
            // 服务器地址按钮
            const copyBtn = document.createElement('button');
            copyBtn.className = 'download-link';
            copyBtn.textContent = translations[currentLang]['nodes.copy_address'] || '复制地址';
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(`${node.server}:${node.port}`)
                .then(() => {
                    copyBtn.textContent = translations[currentLang]['nodes.copied'] || '已复制!';
                    setTimeout(() => {
                        copyBtn.textContent = translations[currentLang]['nodes.copy_address'] || '复制地址';
                    }, 2000);
                })
                .catch(err => {
                    console.error('复制失败:', err);
                    copyBtn.textContent = translations[currentLang]['nodes.copy_failed'] || '复制失败';
                });
            };
            actionCell.appendChild(copyBtn);
        } else {
            actionCell.textContent = translations[currentLang]['nodes.no_action'] || '无操作';
        }
        
        row.appendChild(actionCell);
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    return table;
}

// 全局排序函数
window.sortTable = function(field) {
    if (field === currentSort.field) {
        currentSort.ascending = !currentSort.ascending;
    } else {
        currentSort = { field, ascending: true };
    }
    
    // 更新排序图标
    document.querySelectorAll('.sortable span').forEach(span => {
        span.textContent = '↕️';
    });
    const sortIcon = document.getElementById(`${field}-sort-icon`);
    if (sortIcon) {
        sortIcon.textContent = currentSort.ascending ? '⬆️' : '⬇️';
    }
    
    // 重新渲染节点表格
    render();
};

async function render() {
    // 确保加载状态可见
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'block';
    
    const nodes = await loadNodes();
    
    // 隐藏加载状态
    if (loading) loading.style.display = 'none';
    
    const listContainer = document.getElementById('server-list');
    if (!listContainer) {
        console.error('找不到 server-list 容器');
        return;
    }
    
    // 清空容器
    listContainer.innerHTML = '';
    
    if (nodes.length === 0) {
        const message = document.createElement('div');
        message.className = 'error-message';
        message.innerHTML = `
        <p>⚠️ ${translations[currentLang]['nodes.no_nodes_title'] || '没有找到可用节点'}</p>
        <p>${translations[currentLang]['nodes.no_nodes_message'] || '请稍后再试或联系管理员'}</p>
        <button onclick="location.reload()" style="margin-top:10px; background:#007bff; color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">
            ${translations[currentLang]['nodes.refresh'] || '重新加载'}
        </button>
        `;
        listContainer.appendChild(message);
        return;
    }
    
    // 创建节点表格
    const table = createServerTable(nodes);
    listContainer.appendChild(table);
    
    // 更新获取免费节点按钮
    const ctaBtn = document.getElementById('cta-btn');
    if (ctaBtn) {
        ctaBtn.textContent = `${translations[currentLang]['hero.get_subscription'] || '获取免费节点'} (${nodes.length})`;
        ctaBtn.onclick = () => {
            // 滚动到节点列表
            document.getElementById('server-list').scrollIntoView({ behavior: 'smooth' });
        };
    }
}

// 等 DOM 加载完成再执行
document.addEventListener('DOMContentLoaded', render);

// 暴露重新加载函数给全局
window.reloadNodes = function() {
    render();
};
