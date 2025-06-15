async function loadNodes() {
  // 显示加载状态
  const loading = document.getElementById('loading');
  if (loading) {
    loading.style.display = 'block';
    loading.querySelector('p').textContent = translations[currentLang]['nodes.loading'] || '正在加载节点数据，请稍候...';
  }
  
  try {
    // 添加时间戳防止缓存
    const timestamp = new Date().getTime();
    const res = await fetch(`/nodes.json?t=${timestamp}`, { 
      cache: 'no-store',
      credentials: 'same-origin'  // 修复：确保携带cookie
    });
    
    if (!res.ok) {
      throw new Error(translations[currentLang]['nodes.load_failed'] || '加载节点数据失败');
    }
    
    // 获取响应文本
    const text = await res.text();
    
    // 调试：输出前500个字符
    console.log('nodes.json 内容预览:', text.substring(0, 500));
    
    // 尝试解析JSON
    const data = JSON.parse(text);
    
    // 调试信息
    console.log("成功加载节点数据:", {
      count: data.length,
      firstNode: data[0] || null,
      types: [...new Set(data.map(n => n.type))],
    });
    
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
  } finally {
    // 无论成功失败，最后都会隐藏加载状态
    // 实际隐藏操作在render函数中完成
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

function createServerTable(nodes) {
  const table = document.createElement('table');
  table.className = 'server-table';
  
  // 创建表头（使用翻译）
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>${translations[currentLang]['nodes.name'] || '名称'}</th>
      <th>${translations[currentLang]['nodes.type'] || '类型'}</th>
      <th>${translations[currentLang]['nodes.status'] || '状态'}</th>
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
          if (node.type === 'vmess') fileName += '.yaml';
          else if (node.type === 'ss') fileName += '.yaml';
          else fileName += '.yaml';
          
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
