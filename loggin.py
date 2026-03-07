import customtkinter as ctk
from tkinter import messagebox
from dashbord import DashboardApp  
from database import connect
from hash import hash_sha256
import time

conn=connect()
cursor = conn.cursor(dictionary=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


LOCK_DURATION = 60  
count_dict = {}
locked_accounts = {}



root = ctk.CTk()
root.geometry("750x600")
root.title("Desktop Login")
root.resizable(False, False)
root.configure(fg_color="#1B1B2F")



container = ctk.CTkFrame(root, fg_color="#1B1B2F", corner_radius=0,width=00)
container.pack(fill="both", expand=True)


right_panel = ctk.CTkFrame(container, width=200, height=600, fg_color="#2A2D3E", corner_radius=20)
right_panel.place(relx=0.5, rely=0.5, anchor="center")

title = ctk.CTkLabel(right_panel, text="Login", font=ctk.CTkFont(size=35, weight="bold"))
title.pack(pady=(40, 10))

subtitle = ctk.CTkLabel(right_panel, text="Enter your credentials below",
                        font=ctk.CTkFont(size=15),
                        text_color="#B0B0B0")
subtitle.pack(pady=(0, 20))

roles = ["Admin", "Faculty", "Staff", "Student"]
selected_role = ctk.StringVar(value="Student")  

role_dropdown = ctk.CTkOptionMenu(right_panel, values=roles, variable=selected_role, width=200,
                                  button_color="#4A90E2", button_hover_color="#357ABD",
                                  dropdown_fg_color="#2A2D3E", dropdown_text_color="white")
role_dropdown.pack(pady=(0, 20))

def create_input(parent, icon_text, placeholder, show=None):
    frame = ctk.CTkFrame(parent, fg_color="#3A3D52", corner_radius=10, height=30)
    frame.pack(pady=10, padx=50, fill="x")

    icon = ctk.CTkLabel(frame, text=icon_text, font=ctk.CTkFont(size=20), bg_color="#3A3D52")
    icon.pack(side="left", padx=12)

    entry = ctk.CTkEntry(frame, placeholder_text=placeholder, border_width=0, width=230,
                          fg_color="#3A3D52", font=ctk.CTkFont(size=15), show=show)
    entry.pack(side="left", fill="x", expand=True, padx=5)
    return entry

email_entry = create_input(right_panel, "📧", "Username")
password_entry = create_input(right_panel, "🔒", "Password", show="*")

def login():
    email = email_entry.get().strip()
    password = password_entry.get().strip()
    role = selected_role.get()

    if not email or not password:
        messagebox.showerror("Error", "Please enter username and password")
        return

    if email in locked_accounts:
        unlock_time = locked_accounts[email]
        if time.time() < unlock_time:
            remaining = int(unlock_time - time.time())
            messagebox.showerror("Account Locked", f"Try again in {remaining} seconds")
            return
        else:
            del locked_accounts[email]
            count_dict[email] = 0

    try:
        password=hash_sha256(password)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        if not user or user['password'] != password:
            raise ValueError("Invalid credentials")
        count_dict[email] = 0
        if role == "Admin":
            print(role)
            app = DashboardApp(email)
            root.withdraw()
            app.mainloop()

    except:
        count_dict[email] = count_dict.get(email, 0) + 1
        if count_dict[email] >= 3:
            locked_accounts[email] = time.time() + LOCK_DURATION
            messagebox.showerror("Account Locked", f"Too many failed attempts. Locked for {LOCK_DURATION} seconds")
            return
        messagebox.showerror("Error", "Email, password, or role incorrect")


login_btn = ctk.CTkButton(right_panel, text="Login", command=login,
                          width=280, height=30, fg_color="#4A90E2",
                          hover_color="#357ABD",
                          font=ctk.CTkFont(size=15, weight="bold"))
login_btn.pack(pady=25)
root.bind('<Return>', lambda event: login())

bottom_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
bottom_frame.pack(pady=10)

forgot_btn = ctk.CTkButton(bottom_frame, text="Forgot Password?",
                           command=lambda: messagebox.showinfo("Info", "Please contact Admin"),
                           width=120, fg_color="transparent",
                           hover_color="#3A3D52",
                           text_color="#4A90E2",
                           corner_radius=12,
                           font=ctk.CTkFont(size=14))
forgot_btn.pack(side="left", padx=10)

register_btn = ctk.CTkButton(bottom_frame, text="Create Account",
                            
                             width=120, fg_color="transparent",
                             hover_color="#3A3D52",
                             text_color="#4A90E2",
                             corner_radius=12,
                             font=ctk.CTkFont(size=14))
register_btn.pack(side="left", padx=10)

footer = ctk.CTkLabel(right_panel, text="© 2025 MyApp All rights reserved",
                      font=ctk.CTkFont(size=12),
                      text_color="#6B6B6B")
footer.pack(side="bottom", pady=10)

root.mainloop()