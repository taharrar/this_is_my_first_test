import sqlite3
import hashlib
import os
import pandas as pd
from datetime import datetime
from tkinter import *
from tkinter import messagebox, ttk
from contextlib import contextmanager

from tkinter import filedialog



# ==================== DATABASE UTILITIES ====================
def get_db_connection():
    """Database ulanishini olish uchun funksiya"""
    conn = sqlite3.connect('edu_evaluation.db', timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def db_session():
    """Database transaktsiyalari uchun context manager"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

        
# 1. Ma'lumotlar Bazasini Sozlash
def init_db():
    conn = sqlite3.connect('edu_evaluation.db')
    cursor = conn.cursor()
    
    # Jadval yaratish
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ism TEXT NOT NULL,
        login TEXT UNIQUE NOT NULL,
        parol_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('teacher', 'student'))
    );
    
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nomi TEXT NOT NULL,
        oqituvchi_id INTEGER NOT NULL,
        savollar_soni INTEGER DEFAULT 0,
        FOREIGN KEY (oqituvchi_id) REFERENCES users(id)
    );
    
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL,
        savol_matni TEXT NOT NULL,
        variant_a TEXT NOT NULL,
        variant_b TEXT NOT NULL,
        variant_c TEXT NOT NULL,
        variant_d TEXT NOT NULL,
        togri_javob TEXT CHECK (togri_javob IN ('A', 'B', 'C', 'D')),
        FOREIGN KEY (test_id) REFERENCES tests(id)
    );
    
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oquvchi_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        togri_javoblar INTEGER NOT NULL,
        foiz REAL NOT NULL,
        otganmi BOOLEAN NOT NULL,
        vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (oquvchi_id) REFERENCES users(id),
        FOREIGN KEY (test_id) REFERENCES tests(id)
    );
    
    CREATE TABLE IF NOT EXISTS student_test_attempts (
        oquvchi_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        PRIMARY KEY (oquvchi_id, test_id),
        FOREIGN KEY (oquvchi_id) REFERENCES users(id),
        FOREIGN KEY (test_id) REFERENCES tests(id)
    );
    ''')
    
    # Dastur boshlanganda admin qo'shamiz
    try:
        salt = os.urandom(16).hex()
        parol_hash = hashlib.sha256(('admin123' + salt).encode()).hexdigest()
        cursor.execute('''
        INSERT INTO users (ism, login, parol_hash, salt, role)
        VALUES (?, ?, ?, ?, ?)
        ''', ('Admin', 'admin', parol_hash, salt, 'teacher'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Admin allaqachon mavjud
    
    conn.close()

# 2. Asosiy Tkinter Dasturi
class EduEvaluationApp:
    
    def __init__(self, root):
        self.root = root
        self.root.title("Bilim Baholash Tizimi")
        self.current_user = None
        self.current_test = None
        
        # Dizayn sozlamalari
        self.root.geometry("800x600")
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 12))
        self.style.configure('TLabel', font=('Arial', 12))
        
        self.show_login_screen()  

        style = ttk.Style()
        style.configure("Treeview", 
                        font=('Arial', 10),
                        rowheight=25)
        style.configure("Treeview.Heading", 
                        font=('Arial', 12, 'bold'))

        # Treeviewga alternativ ranglar
        style.map("Treeview",
                background=[('selected', '#347083')],
                foreground=[('selected', 'white')])  

    def setup_ui(self):
        """Dastur interfeysini sozlash"""
        self.root.title("Bilim Baholash Tizimi")
        self.root.geometry("1000x700")
        self.configure_styles()
        self.show_login_screen()
    
    def configure_styles(self):
        """Dastur stilini sozlash"""
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 12), padding=5)
        self.style.configure('TLabel', font=('Arial', 12))
        self.style.configure("Treeview", font=('Arial', 10), rowheight=25)
        self.style.configure("Treeview.Heading", font=('Arial', 12, 'bold'))

    def show_login_screen(self):
        # Kirish oynasini ko'rsatish
        self.clear_window()
        
        Label(self.root, text="Bilim Baholash Tizimi", font=('Arial', 20)).pack(pady=20)
        
        # Foydalanuvchi turi
        self.user_type = StringVar(value="student")
        ttk.Radiobutton(self.root, text="O'quvchi", variable=self.user_type, value="student").pack()
        ttk.Radiobutton(self.root, text="O'qituvchi", variable=self.user_type, value="teacher").pack(pady=10)
        
        # Kirish maydonlari
        ttk.Label(self.root, text="Login:").pack()
        self.login_entry = ttk.Entry(self.root)
        self.login_entry.pack()
        
        ttk.Label(self.root, text="Parol:").pack()
        self.password_entry = ttk.Entry(self.root, show="*")
        self.password_entry.pack(pady=10)
        
        ttk.Button(self.root, text="Kirish", command=self.login).pack(pady=20)
        ttk.Button(self.root, text="Chiqish", command=self.root.quit).pack()
    
    def login(self):
        login = self.login_entry.get()
        password = self.password_entry.get()
        role = self.user_type.get()
        
        conn = sqlite3.connect('edu_evaluation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, ism, parol_hash, salt FROM users 
        WHERE login = ? AND role = ?
        ''', (login, role))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            user_id, ism, stored_hash, salt = user
            new_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            if new_hash == stored_hash:
                self.current_user = {'id': user_id, 'name': ism, 'role': role}
                messagebox.showinfo("Muvaffaqiyat", f"Xush kelibsiz, {ism}!")
                
                if role == 'teacher':
                    self.show_teacher_panel()
                else:
                    self.show_student_panel()
            else:
                messagebox.showerror("Xatolik", "Noto'g'ri parol!")
        else:
            messagebox.showerror("Xatolik", "Foydalanuvchi topilmadi!")

    def show_teacher_panel(self):
        self.clear_window()
        Label(self.root, text=f"O'qituvchi paneli: {self.current_user['name']}", font=('Arial', 16)).pack(pady=20)
        
        ttk.Button(self.root, text="Yangi Test Yaratish", command=self.create_test).pack(pady=10)
        ttk.Button(self.root, text="Yangi O'quvchi Qo'shish", command=self.add_student).pack(pady=10)
        ttk.Button(self.root, text="Test Natijalarini Ko'rish", command=self.show_results).pack(pady=10)
        ttk.Button(self.root, text="Test Natijalarini Yuklash", command=self.export_results_to_excel).pack(pady=10)

        ttk.Button(self.root, text="Chiqish", command=self.show_login_screen).pack(pady=20)

    def add_student(self):
        self.clear_window()
        Label(self.root, text="Yangi O'quvchi Qo'shish", font=('Arial', 16)).pack(pady=20)
        
        ttk.Label(self.root, text="Ism:").pack()
        self.student_name_entry = ttk.Entry(self.root)
        self.student_name_entry.pack()

        ttk.Label(self.root, text="Login:").pack()
        self.student_login_entry = ttk.Entry(self.root)
        self.student_login_entry.pack()
        
        ttk.Label(self.root, text="Parol:").pack()
        self.student_password_entry = ttk.Entry(self.root, show="*")
        self.student_password_entry.pack(pady=10)
        
        ttk.Button(self.root, text="Saqlash", command=self.save_student).pack(pady=20)
        ttk.Button(self.root, text="Orqaga", command=self.show_teacher_panel).pack()

    def save_student(self):
        ism = self.student_name_entry.get()
        login = self.student_login_entry.get()
        parol = self.student_password_entry.get()
        
        if not ism or not login or not parol:
            messagebox.showerror("Xatolik", "Barcha maydonlarni to'ldiring!")
            return
        
        try:
            salt = os.urandom(16).hex()
            parol_hash = hashlib.sha256((parol + salt).encode()).hexdigest()
            
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO users (ism, login, parol_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
                ''', (ism, login, parol_hash, salt, 'student'))
            
            messagebox.showinfo("Muvaffaqiyat", "O'quvchi muvaffaqiyatli qo'shildi!")
            self.show_teacher_panel()
        except sqlite3.IntegrityError:
            messagebox.showerror("Xatolik", "Bu login band!")
        except Exception as e:
            messagebox.showerror("Xatolik", f"Xatolik yuz berdi: {str(e)}")

    def save_student(self):
        ism = self.student_name_entry.get()
        login = self.student_login_entry.get()
        parol = self.student_password_entry.get()
        
        if not ism or not login or not parol:
            messagebox.showerror("Xatolik", "Barcha maydonlarni to'ldiring!")
            return
        
        try:
            salt = os.urandom(16).hex()
            parol_hash = hashlib.sha256((parol + salt).encode()).hexdigest()
            
            conn = sqlite3.connect('edu_evaluation.db')
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO users (ism, login, parol_hash, salt, role)
            VALUES (?, ?, ?, ?, ?)
            ''', (ism, login, parol_hash, salt, 'student'))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Muvaffaqiyat", "O'quvchi muvaffaqiyatli qo'shildi!")
            self.show_teacher_panel()
        except sqlite3.IntegrityError:
            messagebox.showerror("Xatolik", "Bu login band!")

    def create_test(self):
        self.clear_window()
        Label(self.root, text="Yangi Test Yaratish", font=('Arial', 16)).pack(pady=20)
        
        ttk.Label(self.root, text="Test nomi:").pack()
        self.test_name_entry = ttk.Entry(self.root)
        self.test_name_entry.pack()
        
        ttk.Label(self.root, text="Savollar soni:").pack()
        self.question_count_entry = ttk.Entry(self.root)
        self.question_count_entry.pack(pady=10)
        
        ttk.Button(self.root, text="Testni Saqlash", command=self.save_test).pack(pady=20)
        ttk.Button(self.root, text="Orqaga", command=self.show_teacher_panel).pack()
    

    # Save_test section  # test yaratish ; uni saqlash ;        
    def save_test(self):
        test_name = self.test_name_entry.get()
        question_count = self.question_count_entry.get()
        
        if not test_name or not question_count.isdigit():
            messagebox.showerror("Xatolik", "Ma'lumotlarni to'g'ri kiriting!")
            return
        
        question_count = int(question_count)
        
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO tests (nomi, oqituvchi_id, savollar_soni)
                VALUES (?, ?, ?)
                ''', (test_name, self.current_user['id'], question_count))
                test_id = cursor.lastrowid
            
            # Test savollarini kiritish oynasini ochish
            self.show_test_questions_window(test_id, test_name, question_count)
            
        except Exception as e:
            messagebox.showerror("Xatolik", f"Test yaratishda xatolik: {str(e)}")

    def show_test_questions_window(self, test_id, test_name, question_count):
        self.test_questions_window = Toplevel(self.root)
        self.test_questions_window.title(f"Test: {test_name} - Savollar")
        
        self.question_entries = []
        self.variant_a_entries = []
        self.variant_b_entries = []
        self.variant_c_entries = []
        self.variant_d_entries = []
        self.correct_answer_vars = []
        
        for i in range(question_count):
            frame = Frame(self.test_questions_window)
            frame.pack(pady=10, fill=X)
            
            Label(frame, text=f"Savol {i+1}:").pack(anchor=W)
            question_entry = Entry(frame, width=50)
            question_entry.pack(fill=X)
            self.question_entries.append(question_entry)
            
            Label(frame, text="Variantlar:").pack(anchor=W)
            
            variant_frame = Frame(frame)
            variant_frame.pack(fill=X)
            
            Label(variant_frame, text="A:").pack(side=LEFT)
            variant_a = Entry(variant_frame, width=20)
            variant_a.pack(side=LEFT, padx=5)
            self.variant_a_entries.append(variant_a)
            
            Label(variant_frame, text="B:").pack(side=LEFT)
            variant_b = Entry(variant_frame, width=20)
            variant_b.pack(side=LEFT, padx=5)
            self.variant_b_entries.append(variant_b)
            
            Label(variant_frame, text="C:").pack(side=LEFT)
            variant_c = Entry(variant_frame, width=20)
            variant_c.pack(side=LEFT, padx=5)
            self.variant_c_entries.append(variant_c)
            
            Label(variant_frame, text="D:").pack(side=LEFT)
            variant_d = Entry(variant_frame, width=20)
            variant_d.pack(side=LEFT, padx=5)
            self.variant_d_entries.append(variant_d)
            
            correct_var = StringVar(value="A")
            correct_frame = Frame(frame)
            correct_frame.pack(fill=X)
            Label(correct_frame, text="To'g'ri javob:").pack(side=LEFT)
            Radiobutton(correct_frame, text="A", variable=correct_var, value="A").pack(side=LEFT)
            Radiobutton(correct_frame, text="B", variable=correct_var, value="B").pack(side=LEFT)
            Radiobutton(correct_frame, text="C", variable=correct_var, value="C").pack(side=LEFT)
            Radiobutton(correct_frame, text="D", variable=correct_var, value="D").pack(side=LEFT)
            self.correct_answer_vars.append(correct_var)
        
        Button(self.test_questions_window, text="Barcha Savollarni Saqlash", 
            command=lambda: self.save_all_questions(test_id, question_count)).pack(pady=20)

    def save_all_questions(self, test_id, question_count):
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                
                for i in range(question_count):
                    question = self.question_entries[i].get()
                    variant_a = self.variant_a_entries[i].get()
                    variant_b = self.variant_b_entries[i].get()
                    variant_c = self.variant_c_entries[i].get()
                    variant_d = self.variant_d_entries[i].get()
                    correct = self.correct_answer_vars[i].get()
                    
                    if not question or not variant_a or not variant_b or not variant_c or not variant_d:
                        messagebox.showerror("Xatolik", f"Savol {i+1} uchun barcha maydonlarni to'ldiring!")
                        return
                    
                    cursor.execute('''
                    INSERT INTO questions (test_id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (test_id, question, variant_a, variant_b, variant_c, variant_d, correct))
                
                self.test_questions_window.destroy()
                messagebox.showinfo("Muvaffaqiyat", "Test muvaffaqiyatli yaratildi!")
                self.show_teacher_panel()
                
        except Exception as e:
            messagebox.showerror("Xatolik", f"Savollarni saqlashda xatolik: {str(e)}")
    
    # def show_results(self):
    #     self.clear_window()
    #     Label(self.root, text="Test Natijalari", font=('Arial', 16)).pack(pady=20)
        
    #     conn = sqlite3.connect('edu_evaluation.db')
    #     cursor = conn.cursor()
        
    #     cursor.execute('''
    #     SELECT t.nomi, r.togri_javoblar, r.foiz, r.otganmi, r.vaqt 
    #     FROM results r
    #     JOIN tests t ON r.test_id = t.id
    #     WHERE t.oqituvchi_id = ?
    #     ''', (self.current_user['id'],))
        
    #     results = cursor.fetchall()
    #     conn.close()
        
    #     if not results:
    #         Label(self.root, text="Hozircha natijalar mavjud emas").pack()
    #     else:
    #         columns = ('Test nomi', "To'g'ri javoblar", "Foiz", "Holat", "Vaqt")
    #         tree = ttk.Treeview(self.root, columns=columns, show='headings')
            
    #         for col in columns:
    #             tree.heading(col, text=col)
    #             tree.column(col, width=120)
            
    #         for row in results:
    #             holat = "O'tdi" if row[3] else "O'tmadi"
    #             tree.insert('', END, values=(row[0], row[1], f"{row[2]:.1f}%", holat, row[4]))
            
    #         tree.pack(expand=True, fill=BOTH)
        
    #     ttk.Button(self.root, text="Orqaga", command=self.show_teacher_panel).pack(pady=20)
    
    def show_results(self):
        self.clear_window()
        Label(self.root, text="Test Natijalari", font=('Arial', 16, 'bold')).pack(pady=20)

        # Ma'lumotlar bazasi bilan xavfsiz ishlash
        with sqlite3.connect('edu_evaluation.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.nomi, r.togri_javoblar, r.foiz, r.otganmi, r.vaqt 
                FROM results r
                JOIN tests t ON r.test_id = t.id
                WHERE t.oqituvchi_id = ?
            ''', (self.current_user['id'],))
            results = cursor.fetchall()

        if not results:
            Label(self.root, text="📌 Hozircha natijalar mavjud emas", font=('Arial', 12, 'italic')).pack(pady=10)
        else:
            columns = ('Test nomi', "To'g'ri javoblar", "Foiz", "Holat", "Vaqt")
            tree = ttk.Treeview(self.root, columns=columns, show='headings')

            # Ustunlar sarlavhalari
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120, stretch=True)
            
            # Rangli natijalar
            tree.tag_configure('passed', background='#d4edda')  # Yashil (O'tdi)
            tree.tag_configure('failed', background='#f8d7da')  # Qizil (O'tmadi)

            for row in results:
                holat = "O'tdi" if row[3] else "O'tmadi"
                tag = 'passed' if row[3] else 'failed'
                tree.insert('', END, values=(row[0], row[1], f"{row[2]:.1f}%", holat, row[4]), tags=(tag,))

            tree.pack(expand=True, fill=BOTH)

        ttk.Button(self.root, text="⬅️ Orqaga", command=self.show_teacher_panel).pack(pady=20)


    def export_results_to_excel(self):
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT u.ism, t.nomi, r.togri_javoblar, r.savollar_soni, r.foiz, r.otganmi, r.vaqt
                FROM results r
                JOIN users u ON r.oquvchi_id = u.id
                JOIN tests t ON r.test_id = t.id
                WHERE t.oqituvchi_id = ?
                ''', (self.current_user['id'],))
                
                results = cursor.fetchall()
    
            df = pd.DataFrame(results, columns=["O'quvchi", "Test", "To'g'ri javoblar", "Savollar soni", "Foiz", "Holat", "Vaqt"])
            df["Holat"] = df["Holat"].apply(lambda x: "O'tdi" if x else "O'tmadi")
            df.to_excel('natijalar.xlsx', index=False)
            messagebox.showinfo("Muvaffaqiyatli", "Natijalar Excel fayliga saqlandi!")

            # Fayl joylashuvini tanlash
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Natijalarni saqlash"
            )
            
            if not file_path:  # Agar foydalanuvchi bekor qilsa
                return
                
            df.to_excel(file_path, index=False)
            self.show_message("Muvaffaqiyat", f"Natijalar {file_path} fayliga saqlandi!")
            
        except Exception as e:
            self.show_error("Xatolik", f"Export qilishda xatolik: {str(e)}")
    def show_student_panel(self):
        self.clear_window()
        Label(self.root, text=f"O'quvchi paneli: {self.current_user['name']}", font=('Arial', 16)).pack(pady=20)
        
        conn = sqlite3.connect('edu_evaluation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT t.id, t.nomi 
        FROM tests t
        WHERE t.id NOT IN (
            SELECT test_id FROM student_test_attempts 
            WHERE oquvchi_id = ?
        )
        ''', (self.current_user['id'],))
        
        available_tests = cursor.fetchall()
        conn.close()
        
        if not available_tests:
            Label(self.root, text="Hozircha testlar mavjud emas yoki siz barchasini ishlagansiz").pack()
        else:
            Label(self.root, text="Mavjud testlar:").pack()
            
            for test_id, test_name in available_tests:
                ttk.Button(self.root, text=test_name, 
                          command=lambda tid=test_id: self.start_test(tid)).pack(pady=5)
        
        ttk.Button(self.root, text="Natijalarni ko'rish", command=self.show_student_results).pack(pady=20)
        ttk.Button(self.root, text="Chiqish", command=self.show_login_screen).pack()
    
    def start_test(self, test_id):
        self.current_test = test_id
        self.clear_window()
        
        conn = sqlite3.connect('edu_evaluation.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT savol_matni, variant_a, variant_b, variant_c, variant_d FROM questions WHERE test_id = ?', (test_id,))
        questions = cursor.fetchall()
        conn.close()
        
        self.answers = []
        self.current_question = 0
        
        Label(self.root, text=f"Test: {test_id} - Savol {self.current_question+1}/{len(questions)}", 
              font=('Arial', 14)).pack(pady=10)
        
        self.question_label = Label(self.root, text=questions[self.current_question][0], wraplength=700)
        self.question_label.pack(pady=10)
        
        self.answer_var = StringVar()
        Radiobutton(self.root, text=questions[self.current_question][1], variable=self.answer_var, value="A").pack(anchor=W)
        Radiobutton(self.root, text=questions[self.current_question][2], variable=self.answer_var, value="B").pack(anchor=W)
        Radiobutton(self.root, text=questions[self.current_question][3], variable=self.answer_var, value="C").pack(anchor=W)
        Radiobutton(self.root, text=questions[self.current_question][4], variable=self.answer_var, value="D").pack(anchor=W)
        
        ttk.Button(self.root, text="Keyingi savol", command=lambda: self.next_question(test_id, questions)).pack(pady=20)
    
    def next_question(self, test_id, questions):
        if not self.answer_var.get():
            messagebox.showerror("Xatolik", "Iltimos, javobni belgilang!")
            return
        
        self.answers.append(self.answer_var.get())
        self.current_question += 1
        
        if self.current_question < len(questions):
            self.clear_window()
            Label(self.root, text=f"Test: {test_id} - Savol {self.current_question+1}/{len(questions)}", 
                  font=('Arial', 14)).pack(pady=10)
            
            self.question_label = Label(self.root, text=questions[self.current_question][0], wraplength=700)
            self.question_label.pack(pady=10)
            
            self.answer_var = StringVar()
            Radiobutton(self.root, text=questions[self.current_question][1], variable=self.answer_var, value="A").pack(anchor=W)
            Radiobutton(self.root, text=questions[self.current_question][2], variable=self.answer_var, value="B").pack(anchor=W)
            Radiobutton(self.root, text=questions[self.current_question][3], variable=self.answer_var, value="C").pack(anchor=W)
            Radiobutton(self.root, text=questions[self.current_question][4], variable=self.answer_var, value="D").pack(anchor=W)
            
            if self.current_question == len(questions)-1:
                ttk.Button(self.root, text="Yakunlash", command=lambda: self.finish_test(test_id, questions)).pack(pady=20)
            else:
                ttk.Button(self.root, text="Keyingi savol", command=lambda: self.next_question(test_id, questions)).pack(pady=20)
        else:
            self.finish_test(test_id, questions)
    
    def finish_test(self, test_id, questions):
        self.answers.append(self.answer_var.get())
        
        # To'g'ri javoblarni olish
        conn = sqlite3.connect('edu_evaluation.db')
        cursor = conn.cursor()
        cursor.execute('SELECT togri_javob FROM questions WHERE test_id = ? ORDER BY id', (test_id,))
        correct_answers = [row[0] for row in cursor.fetchall()]
        
        # Baholash
        correct = sum(1 for i in range(len(questions)) if self.answers[i] == correct_answers[i])
        percentage = (correct / len(questions)) * 100
        passed = percentage >= 60
        
        # Natijalarni saqlash
        cursor.execute('''
        INSERT INTO results (oquvchi_id, test_id, togri_javoblar, foiz, otganmi)
        VALUES (?, ?, ?, ?, ?)
        ''', (self.current_user['id'], test_id, correct, percentage, passed))
        
        # Test ishlanganligini belgilash
        cursor.execute('''
        INSERT INTO student_test_attempts (oquvchi_id, test_id)
        VALUES (?, ?)
        ''', (self.current_user['id'], test_id))
        
        conn.commit()
        conn.close()
        
        # Natijalarni ko'rsatish
        messagebox.showinfo(
            "Test yakunlandi",
            f"Natijangiz: {correct}/{len(questions)}\n"
            f"Foiz: {percentage:.1f}%\n"
            f"Holat: {"O'tdingiz! ✅" if passed else "O'tmadingiz ❌"}"
        )
        
        self.show_student_panel()
    
    def show_student_results(self):
        self.clear_window()
        Label(self.root, text="Mening Natijalarim", font=('Arial', 16)).pack(pady=20)
        
        conn = sqlite3.connect('edu_evaluation.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT t.nomi, r.togri_javoblar, r.foiz, r.otganmi, r.vaqt 
        FROM results r
        JOIN tests t ON r.test_id = t.id
        WHERE r.oquvchi_id = ?
        ''', (self.current_user['id'],))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            Label(self.root, text="Hozircha natijalar mavjud emas").pack()
        else:
            columns = ('Test nomi', "To'g'ri javoblar", "Foiz", "Holat", "Vaqt")
            tree = ttk.Treeview(self.root, columns=columns, show='headings')
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            
            for row in results:
                holat = "O'tdi" if row[3] else "O'tmadi"
                tree.insert('', END, values=(row[0], row[1], f"{row[2]:.1f}%", holat, row[4]))
            
            tree.pack(expand=True, fill=BOTH)
        
        ttk.Button(self.root, text="Orqaga", command=self.show_student_panel).pack(pady=20)
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_message(self, title, message):
        """Xabar oynasini ko'rsatish"""
        messagebox.showinfo(title, message)
    
    def show_error(self, title, message):
        """Xato xabarini ko'rsatish"""
        messagebox.showerror(title, message)



# Dasturni ishga tushurish
if __name__ == "__main__":
    init_db()
    root = Tk()
    app = EduEvaluationApp(root)
    root.mainloop()