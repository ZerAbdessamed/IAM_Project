@app.route("/secret-verify", methods=["POST"])
def mfa_verify():
    if "pre_auth" not in session:
        return {"msg": "unauthorized"}, 403

    admin = Admin.query.get(session["pre_auth"])
    data = request.json

    if check_password_hash(admin.secret_answer_hash, data["answer"]):
        session.pop("pre_auth")

        session["admin_id"] = admin.id
        session["role"] = "admin"

        return {"msg": "login success"}

    return {"msg": "wrong answer"}, 401