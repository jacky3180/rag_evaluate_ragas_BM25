/**
 * 统一导航菜单组件
 * 提供跨页面的导航功能
 */

class NavigationMenu {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.init();
    }

    /**
     * 获取当前页面标识
     */
    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('history.html')) return 'history';
        if (path.includes('standardDataset_build.html')) return 'build';
        if (path === '/' || path.includes('index.html')) return 'home';
        return 'home';
    }

    /**
     * 初始化导航菜单
     */
    init() {
        this.createNavigationHTML();
        this.bindEvents();
        this.setActiveMenuItem();
    }

    /**
     * 创建导航菜单HTML
     */
    createNavigationHTML() {
        const navHTML = `
            <nav class="main-navigation">
                <div class="nav-container">
                    <div class="nav-brand">
                        <a href="/" class="brand-link">
                            <i class="fas fa-chart-line"></i>
                            <span>RAG评估系统</span>
                        </a>
                    </div>
                    
                    <div class="nav-menu">
                        <div class="nav-item">
                            <a href="/" class="nav-link ${this.currentPage === 'home' ? 'active' : ''}" data-page="home">
                                <i class="fas fa-home"></i>
                                <span>首页</span>
                            </a>
                        </div>
                        
                        <div class="nav-item">
                            <a href="/static/history.html" class="nav-link ${this.currentPage === 'history' ? 'active' : ''}" data-page="history">
                                <i class="fas fa-chart-bar"></i>
                                <span>历史数据分析</span>
                            </a>
                        </div>
                        
                        <div class="nav-item">
                            <a href="/static/standardDataset_build.html" class="nav-link ${this.currentPage === 'build' ? 'active' : ''}" data-page="build">
                                <i class="fas fa-database"></i>
                                <span>构建数据集</span>
                            </a>
                        </div>
                    </div>
                    
                    <div class="nav-actions">
                        <button class="nav-action-btn" onclick="openUploadDialog()" title="上传待评测文档">
                            <i class="fas fa-upload"></i>
                        </button>
                        <button class="nav-action-btn" onclick="openSettings()" title="设置">
                            <i class="fas fa-cog"></i>
                        </button>
                    </div>
                    
                    <div class="nav-toggle" onclick="toggleMobileMenu()">
                        <i class="fas fa-bars"></i>
                    </div>
                </div>
            </nav>
        `;

        // 插入到页面顶部
        document.body.insertAdjacentHTML('afterbegin', navHTML);
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 导航链接点击事件
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetPage = link.dataset.page;
                this.navigateToPage(targetPage);
            });
        });

        // 移动端菜单切换
        window.toggleMobileMenu = () => {
            const navMenu = document.querySelector('.nav-menu');
            const navToggle = document.querySelector('.nav-toggle');
            
            navMenu.classList.toggle('mobile-active');
            navToggle.classList.toggle('active');
        };

        // 点击外部关闭移动端菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.main-navigation')) {
                const navMenu = document.querySelector('.nav-menu');
                const navToggle = document.querySelector('.nav-toggle');
                navMenu.classList.remove('mobile-active');
                navToggle.classList.remove('active');
            }
        });
    }

    /**
     * 设置活动菜单项
     */
    setActiveMenuItem() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const activeLink = document.querySelector(`[data-page="${this.currentPage}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    /**
     * 导航到指定页面
     */
    navigateToPage(page) {
        const routes = {
            'home': '/',
            'history': '/static/history.html',
            'build': '/static/standardDataset_build.html'
        };

        if (routes[page]) {
            window.location.href = routes[page];
        }
    }
}

// 全局函数 - 打开上传对话框
window.openUploadDialog = function() {
    const uploadModal = document.getElementById('uploadModal');
    if (uploadModal) {
        uploadModal.style.display = 'block';
        
        // 重置上传区域
        const uploadArea = document.getElementById('uploadArea');
        const uploadBtn = document.getElementById('uploadBtn');
        const fileInput = document.getElementById('fileInput');
        
        if (uploadArea) {
            uploadArea.classList.remove('file-selected');
            const uploadText = uploadArea.querySelector('.upload-text h3');
            const uploadSubtext = uploadArea.querySelector('.upload-text p');
            if (uploadText) uploadText.textContent = '点击或拖拽文件到此处上传';
            if (uploadSubtext) uploadSubtext.textContent = '支持 .xlsx 格式的Excel文档';
        }
        
        if (uploadBtn) uploadBtn.disabled = true;
        if (fileInput) fileInput.value = '';
        
        // 清空选中的文件
        if (window.selectedFile) {
            window.selectedFile = null;
        }
    }
};

// 全局函数 - 关闭上传对话框
window.closeUploadDialog = function() {
    const uploadModal = document.getElementById('uploadModal');
    if (uploadModal) {
        uploadModal.style.display = 'none';
    }
};

// 注意：openSettings() 函数已在 script.js 中实现，这里不需要重复定义

// 页面加载完成后初始化导航
document.addEventListener('DOMContentLoaded', function() {
    new NavigationMenu();
});
