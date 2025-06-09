async function loadNodes() {
  try {
    const res = await fetch('/nodes.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.error('加载 nodes.json 出错：', error);
    return [];
  }
}

function getProtocolType(type) {
  const types = {
    "vmess": "VMess",
    "ss": "Shadowsocks",
    "trojan": "Trojan",
    "unknown": "未知协议"
  };
  return types[type] || type;
}

function createServerTable(nodes) {
  const table = document.createElement('table');
  table.className = 'server-table';
  
  // 创建表头
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>名称</th>
      <th>类型</th>
      <th>来源</th>
      <th>操作</th>
    </tr>
  `;
  table.appendChild(thead);
  
  // 创建表格主体
  const tbody = document.createElement('tbody');
  
  nodes.forEach(node => {
    const row = document.createElement('tr');
    
    // 名称列
    const nameCell = document.createElement('td');
    nameCell.textContent = node.name || '未知节点';
    row.appendChild(nameCell);
    
    // 类型列
    const typeCell = document.createElement('td');
    typeCell.textContent = getProtocolType(node.type);
    row.appendChild(typeCell);
    
    // 来源列
    const sourceCell = document.createElement('td');
    if (node.source) {
      const sourceLink = document.createElement('a');
      sourceLink.href = node.source;
      sourceLink.target = '_blank';
      sourceLink.textContent = '查看来源';
      sourceCell.appendChild(sourceLink);
    } else {
      sourceCell.textContent = '未知来源';
    }
    row.appendChild(sourceCell);
    
    // 操作列
    const actionCell = document.createElement('td');
    
    // 根据节点类型创建不同的操作
    if (node.config) {
      // 配置下载按钮
      const downloadBtn = document.createElement('button');
      downloadBtn.className = 'download-link';
      downloadBtn.textContent = '下载配置';
      downloadBtn.onclick = () => {
        // 创建配置文件下载
        const blob = new Blob([node.config], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${node.name.replace(/[^a-z0-9]/gi, '_')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      };
      actionCell.appendChild(downloadBtn);
    } else if (node.server && node.port) {
      // 服务器地址按钮
      const copyBtn = document.createElement('button');
      copyBtn.className = 'download-link';
      copyBtn.textContent = '复制地址';
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(`${node.server}:${node.port}`);
        copyBtn.textContent = '已复制!';
        setTimeout(() => {
          copyBtn.textContent = '复制地址';
        }, 2000);
      };
      actionCell.appendChild(copyBtn);
    } else {
      actionCell.textContent = '无操作';
    }
    
    row.appendChild(actionCell);
    tbody.appendChild(row);
  });
  
  table.appendChild(tbody);
  return table;
}

async function render() {
  const nodes = await loadNodes();
  
  const listContainer = document.getElementById('server-list');
  if (!listContainer) {
    console.error('找不到 server-list 容器');
    return;
  }
  
  // 清空容器
  listContainer.innerHTML = '';
  
  if (nodes.length === 0) {
    const message = document.createElement('p');
    message.textContent = '没有找到可用节点，请稍后再试';
    message.style.textAlign = 'center';
    message.style.padding = '20px';
    listContainer.appendChild(message);
    return;
  }
  
  // 创建节点表格
  const table = createServerTable(nodes);
  listContainer.appendChild(table);
  
  // 更新获取免费节点按钮
  const ctaBtn = document.querySelector('.cta-btn');
  if (ctaBtn) {
    ctaBtn.textContent = `获取免费节点 (${nodes.length})`;
    ctaBtn.onclick = () => {
      // 滚动到节点列表
      document.getElementById('server-list').scrollIntoView({ behavior: 'smooth' });
    };
  }
}

// 等 DOM 加载完成再执行
document.addEventListener('DOMContentLoaded', render);
