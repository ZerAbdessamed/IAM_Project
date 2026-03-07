import customtkinter as ctk
from tkinter import messagebox, ttk
import mysql.connector.errors
from database import connect
conn=connect()
cursor = conn.cursor(dictionary=True)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DashboardApp(ctk.CTk):
    def __init__(self, user_email):
        super().__init__()

        self.user_email = user_email
        self.title("University Identity Management Dashboard")
        self.geometry("1200x700")
        self.minsize(1000,600)

        self.SIDEBAR_COLOR = "#1E1E2E"
        self.MAIN_COLOR = "#2A2D3E"

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.current_section = "Dashboard"

        self.create_sidebar()
        self.create_main_content()
        self.load_dashboard_stats()


    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=self.SIDEBAR_COLOR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(self.sidebar, text="🎓 UniManage", font=ctk.CTkFont(size=24, weight="bold"), text_color="white")
        logo.pack(pady=(30, 40))

        self.create_sidebar_button("🏠 Dashboard", self.load_dashboard_stats)
        self.create_sidebar_button("🎓 Students", lambda: self.load_section("Student"))
        self.create_sidebar_button("👩‍🏫 Faculty", lambda: self.load_section("Faculty"))
        self.create_sidebar_button("🧑‍💼 Staff", lambda: self.load_section("Staff"))
        self.create_sidebar_button("🎓 PhD", lambda: self.load_section("PhD"))
        self.create_sidebar_button("🕒 Temporary", lambda: self.load_section("Temporary"))
        self.create_sidebar_button("🎓 Alumni", lambda: self.load_section("Alumni"))

        logout_btn = ctk.CTkButton(self.sidebar, text="🚪 Logout", fg_color="#CC3333", hover_color="#A32929", command=self.logout)
        logout_btn.pack(side="bottom", pady=30, padx=20, fill="x")

    def create_sidebar_button(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", hover_color="#34345A",
                             anchor="w", font=ctk.CTkFont(size=15), command=command)
        btn.pack(fill="x", padx=20, pady=6)

   
    def create_main_content(self):
        self.main = ctk.CTkFrame(self, fg_color=self.MAIN_COLOR, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure((0,1), weight=1)

        self.header_label = ctk.CTkLabel(self.main, text=f"Welcome 👋", font=ctk.CTkFont(size=36, weight="bold"))
        self.header_label.grid(row=0, column=0, columnspan=2, padx=30, pady=(30,5), sticky="w")

        self.email_label = ctk.CTkLabel(self.main, text=f"Logged in as: {self.user_email}", font=ctk.CTkFont(size=14), text_color="#B0B0B0")
        self.email_label.grid(row=1, column=0, columnspan=2, padx=30, pady=(0,30), sticky="w")

        self.content_frame = ctk.CTkFrame(self.main, fg_color=self.MAIN_COLOR)
        self.content_frame.grid(row=2, column=0, columnspan=2, padx=30, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

 
    def load_dashboard_stats(self):
        self.current_section = "Dashboard"
        self.header_label.configure(text="Dashboard")
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        stats = {}
        sections = ["Student","Faculty","Staff","PhD","Temporary","Alumni"]
        for t in sections:
            try:
                cursor.execute("SELECT COUNT(*) AS count FROM persons WHERE type=%s", (t,))
                stats[t] = cursor.fetchone()['count']
            except mysql.connector.Error:
                stats[t] = 0  

        row = 0
        col = 0
        for key, value in stats.items():
            self.create_card(key, value, row, col)
            col +=1
            if col > 1:
                col=0
                row +=1


    def load_section(self, section_type):
        self.current_section = section_type
        self.header_label.configure(text=f"{section_type}s Management")
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        columns = ("ID","First Name","Last Name","Email","Phone","Status")

        search_frame = ctk.CTkFrame(self.content_frame, fg_color=self.MAIN_COLOR)
        search_frame.pack(fill="x", padx=10, pady=(5,0))

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search...", textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(10,5), pady=5)

        tree_frame = ctk.CTkFrame(self.content_frame)
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(fill="both", expand=True, side="left", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        def load_data():
            for item in tree.get_children():
                tree.delete(item)
            cursor.execute("SELECT * FROM persons WHERE type=%s", (section_type,))
            rows = cursor.fetchall()
            print(rows)
            for row in rows:
                if search_var.get().lower() in (str(row['first_name'])+str(row['last_name'])+str(row['email'])+str(row['phone'])+str(row['status'])).lower():
                    tree.insert("", "end", values=(row['unique_id'], row['first_name'], row['last_name'], row['email'], row['phone'], row['status']))

        search_btn = ctk.CTkButton(search_frame, text="Search", fg_color="#3498db", command=load_data)
        search_btn.pack(side="left", padx=(5,10), pady=5)
        search_var.trace("w", lambda *args: load_data())
        load_data()

     
        def add_record():
            def save_new():
                f = entry_fname.get()
                l = entry_lname.get()
                e = entry_email.get()
                p = entry_phone.get()
                s = entry_status.get()
                if f and l and e and p and s:
                    cursor.execute("INSERT INTO persons (first_name,last_name,email,phone,status,type) VALUES (%s,%s,%s,%s,%s,%s)",
                                   (f,l,e,p,s,section_type))
                    conn.commit()
                    load_data()
                    add_win.destroy()
                else:
                    messagebox.showwarning("Warning","Please fill all fields!")

            add_win = ctk.CTkToplevel(self)
            add_win.title("Add Record")
            add_win.geometry("600x450")
            labels = ["First Name","Last Name","Email","Phone","Status"]
            entries = []
            for i, text in enumerate(labels):
                ctk.CTkLabel(add_win, text=text).pack(pady=(10 if i==0 else 5,0))
                entry = ctk.CTkEntry(add_win)
                entry.pack(pady=5)
                entries.append(entry)
            entry_fname, entry_lname, entry_email, entry_phone, entry_status = entries
            save_btn = ctk.CTkButton(add_win, text="Save", command=save_new)
            save_btn.pack(pady=10)

        def edit_record():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning","Select a record to edit!")
                return
            item = tree.item(selected)
            values = item['values']
            uid = values[0]

            def save_edit():
                f = entry_fname.get()
                l = entry_lname.get()
                e = entry_email.get()
                p = entry_phone.get()
                s = entry_status.get()
                if f and l and e and p and s:
                    cursor.execute("UPDATE persons SET first_name=%s,last_name=%s,email=%s,phone=%s,status=%s WHERE unique_id=%s",
                                   (f,l,e,p,s,uid))
                    conn.commit()
                    load_data()
                    edit_win.destroy()
                else:
                    messagebox.showwarning("Warning","Please fill all fields!")

            edit_win = ctk.CTkToplevel(self)
            edit_win.title("Edit Record")
            edit_win.geometry("600x450")
            labels = ["First Name","Last Name","Email","Phone","Status"]
            entries = []
            for i, text in enumerate(labels):
                ctk.CTkLabel(edit_win, text=text).pack(pady=(10 if i==0 else 5,0))
                entry = ctk.CTkEntry(edit_win)
                entry.insert(0, values[i+1])
                entry.pack(pady=5)
                entries.append(entry)
            entry_fname, entry_lname, entry_email, entry_phone, entry_status = entries
            save_btn = ctk.CTkButton(edit_win, text="Save", command=save_edit)
            save_btn.pack(pady=10)

        def delete_record():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning","Select a record to delete!")
                return
            item = tree.item(selected)
            uid = item['values'][0]
            if messagebox.askyesno("Confirm","Are you sure you want to delete this record?"):
                cursor.execute("DELETE FROM persons WHERE unique_id=%s",(uid,))
                conn.commit()
                load_data()

      
        btn_frame = ctk.CTkFrame(self.content_frame)
        btn_frame.pack(fill="x", pady=5)
        add_btn = ctk.CTkButton(btn_frame, text="Add", fg_color="#2ecc71", command=add_record)
        edit_btn = ctk.CTkButton(btn_frame, text="Edit", fg_color="#3498db", command=edit_record)
        delete_btn = ctk.CTkButton(btn_frame, text="Delete", fg_color="#e74c3c", command=delete_record)
        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", fg_color="#9b59b6", command=load_data)

        for b in [add_btn, edit_btn, delete_btn, refresh_btn]:
            b.pack(side="left", padx=10)


    def create_card(self, title, value, row, col):
        card = ctk.CTkFrame(self.content_frame, fg_color="#1F2233", corner_radius=16)
        card.grid(row=row, column=col, padx=25, pady=15, sticky="nsew")

        title_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16), text_color="#B0B0B0")
        title_lbl.pack(anchor="w", padx=20, pady=(15,5))

        value_lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=30, weight="bold"))
        value_lbl.pack(anchor="w", padx=20, pady=(0,20))

 
    def logout(self):
        if messagebox.askyesno("Logout","Are you sure you want to logout?"):
            self.destroy()


if __name__ == "__main__":
    app = DashboardApp(user_email="admin@university.com")
    app.mainloop()