class StudentSystem {
    constructor() {
        this.currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        this.init();
    }

    init() {
        this.setupRoomJoin();
        this.setupAssignmentSubmission();
        this.setupProjectSubmission();
        this.setupNavigation();
    }

    setupRoomJoin() {
        const joinForm = document.getElementById('joinRoomForm');
        if (joinForm) {
            joinForm.addEventListener('submit', this.handleRoomJoin.bind(this));
        }
    }

    setupAssignmentSubmission() {
        // إعداد مستمعين لتسليم الواجبات
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="submit-assignment"]')) {
                this.showAssignmentModal(e.target.closest('[data-assignment-id]'));
            }
        });
    }

    setupProjectSubmission() {
        const projectForm = document.getElementById('projectForm');
        if (projectForm) {
            projectForm.addEventListener('submit', this.handleProjectSubmit.bind(this));
        }
    }

    setupNavigation() {
        // التنقل السلس
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    async handleRoomJoin(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const roomCode = formData.get('roomCode');
        
        try {
            const response = await schoolSystem.apiCall('/api/join_room', {
                method: 'POST',
                body: formData
            });
            
            if (response.success) {
                schoolSystem.showNotification(`تم الانضمام إلى غرفة ${response.room_name} بنجاح!`, 'success');
                schoolSystem.closeModal('joinRoomModal');
                
                // إعادة تحميل الصفحة بعد ثانيتين
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                schoolSystem.showNotification(response.error, 'error');
            }
        } catch (error) {
            schoolSystem.showNotification('حدث خطأ أثناء الانضمام للغرفة', 'error');
        }
    }

    showAssignmentModal(assignmentElement) {
        const assignmentId = assignmentElement.getAttribute('data-assignment-id');
        // هنا سيتم جلب بيانات الواجب وعرضها
        schoolSystem.showModal('assignmentModal');
    }

    async handleProjectSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        
        try {
            const response = await schoolSystem.apiCall('/api/submit_project', {
                method: 'POST',
                body: formData
            });
            
            if (response.success) {
                schoolSystem.showNotification('تم إرسال المشروع/الرأي بنجاح!', 'success');
                e.target.reset();
                
                // إعادة تحميل قائمة المشاريع
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                schoolSystem.showNotification(response.error, 'error');
            }
        } catch (error) {
            schoolSystem.showNotification('حدث خطأ أثناء إرسال المشروع', 'error');
        }
    }

    enterRoom(roomId) {
        // في التطبيق الحقيقي، هنا سيتم فتح نافذة الدردشة
        schoolSystem.showNotification('جاري فتح الغرفة الدراسية...', 'info');
        
        // محاكاة فتح الغرفة
        setTimeout(() => {
            schoolSystem.showNotification('تم الدخول إلى الغرفة بنجاح!', 'success');
        }, 1000);
    }

    viewAssignment(assignmentId) {
        // عرض تفاصيل الواجب
        schoolSystem.showNotification(`جاري تحميل الواجب #${assignmentId}...`, 'info');
        
        // في التطبيق الحقيقي، هنا سيتم جلب بيانات الواجب وعرضها
        setTimeout(() => {
            this.showAssignmentDetails(assignmentId);
        }, 500);
    }

    showAssignmentDetails(assignmentId) {
        // عرض تفاصيل الواجب في مودال
        const modalContent = `
            <h3>تفاصيل الواجب</h3>
            <div class="assignment-details">
                <p><strong>معرف الواجب:</strong> ${assignmentId}</p>
                <p>هذه نافذة معاينة الواجب. في التطبيق الكامل، سيتم جلب البيانات من الخادم.</p>
            </div>
            <div class="form-group">
                <textarea placeholder="أدخل حلك هنا..." rows="6"></textarea>
            </div>
            <button class="btn btn-primary" onclick="submitAssignmentSolution(${assignmentId})">
                <i class="fas fa-paper-plane"></i>
                تسليم الحل
            </button>
        `;
        
        document.getElementById('assignmentContent').innerHTML = modalContent;
        schoolSystem.showModal('assignmentModal');
    }

    async submitAssignmentSolution(assignmentId) {
        const solution = document.querySelector('#assignmentModal textarea').value;
        
        if (!solution.trim()) {
            schoolSystem.showNotification('يرجى إدخال حل الواجب', 'error');
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('assignment_id', assignmentId);
            formData.append('solution', solution);
            
            const response = await schoolSystem.apiCall('/api/submit_assignment', {
                method: 'POST',
                body: formData
            });
            
            if (response.success) {
                schoolSystem.showNotification('تم تسليم الواجب بنجاح!', 'success');
                schoolSystem.closeModal('assignmentModal');
            } else {
                schoolSystem.showNotification(response.error, 'error');
            }
        } catch (error) {
            schoolSystem.showNotification('حدث خطأ أثناء تسليم الواجب', 'error');
        }
    }
}

// تهيئة نظام الطالب
document.addEventListener('DOMContentLoaded', () => {
    window.studentSystem = new StudentSystem();
});

// دوال عامة للطالب (للاستخدام في HTML)
function joinRoom() {
    schoolSystem.showModal('joinRoomModal');
}

function enterRoom(roomId) {
    window.studentSystem.enterRoom(roomId);
}

function viewAssignment(assignmentId) {
    window.studentSystem.viewAssignment(assignmentId);
}

function closeModal(modalId) {
    schoolSystem.closeModal(modalId);
}

function submitAssignmentSolution(assignmentId) {
    window.studentSystem.submitAssignmentSolution(assignmentId);
}