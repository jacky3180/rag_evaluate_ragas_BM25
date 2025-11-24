/**
 * 防抖节流工具函数
 * 用于优化高频事件处理，提升性能
 */

/**
 * 防抖函数
 * 在事件被触发n秒后再执行回调，如果在这n秒内又被触发，则重新计时
 * 
 * @param {Function} func - 要执行的函数
 * @param {Number} wait - 等待时间（毫秒）
 * @param {Boolean} immediate - 是否立即执行
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait = 300, immediate = false) {
    let timeout;
    
    return function executedFunction() {
        const context = this;
        const args = arguments;
        
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        
        const callNow = immediate && !timeout;
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        
        if (callNow) func.apply(context, args);
    };
}

/**
 * 节流函数
 * 规定时间内，只能触发一次函数
 * 
 * @param {Function} func - 要执行的函数
 * @param {Number} limit - 时间间隔（毫秒）
 * @returns {Function} 节流后的函数
 */
function throttle(func, limit = 300) {
    let inThrottle;
    
    return function() {
        const context = this;
        const args = arguments;
        
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 请求动画帧节流
 * 使用requestAnimationFrame来节流函数调用
 * 
 * @param {Function} func - 要执行的函数
 * @returns {Function} 节流后的函数
 */
function rafThrottle(func) {
    let rafId = null;
    
    return function() {
        const context = this;
        const args = arguments;
        
        if (rafId === null) {
            rafId = requestAnimationFrame(() => {
                func.apply(context, args);
                rafId = null;
            });
        }
    };
}

// 导出函数（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        throttle,
        rafThrottle
    };
}

