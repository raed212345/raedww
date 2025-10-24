// دوال مساعدة عامة
function showLoading() {
    document.body.style.cursor = 'wait';
}

function hideLoading() {
    document.body.style.cursor = 'default';
}

function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        ${message}
        <span class="close-alert">&times;</span>
    `;
    
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(alert, mainContent.firstChild);
    }
    
    // إزالة التنبيه بعد 5 ثواني
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// إغلاق التنبيهات
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('close-alert')) {
        e.target.parentElement.remove();
    }
});

// إدارة النماذج
document.addEventListener('DOMContentLoaded', function() {
    // منع إرسال النماذج المزدوج
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري المعالجة...';
                
                // إعادة تمكين الزر بعد 5 ثواني
                setTimeout(() => {
                    submitBtn.disabled = false;
                    const originalText = submitBtn.getAttribute('data-original-text') || 'إرسال';
                    submitBtn.innerHTML = originalText;
                }, 5000);
            }
        });
    });
});