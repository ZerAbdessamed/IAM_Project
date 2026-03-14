// static/js/password_strength.js
document.addEventListener("DOMContentLoaded", function() {
    const passwordInput = document.getElementById("password");
    const strengthSpan = document.getElementById("password-strength");

    if (!passwordInput || !strengthSpan) return;

    passwordInput.addEventListener("input", async function() {
        const pwd = this.value;

        if (!pwd) {
            strengthSpan.innerHTML = "Password strength: ";
            passwordInput.style.borderColor = "";
            return;
        }

        try {
            const response = await fetch("/identity/check_password_strength", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password: pwd })
            });

            const data = await response.json();
            const strength = data.strength.toLowerCase(); 

            let color = "black";
            if (strength === "weak") color = "red";
            else if (strength === "medium") color = "orange";
            else if (strength === "strong") color = "green";

         
            strengthSpan.innerHTML = `Password strength: <span style="color: ${color}; font-weight: bold;">${data.strength}</span>`;

    
        } catch (error) {
            console.error("Password strength check failed:", error);
        }
    });
});
