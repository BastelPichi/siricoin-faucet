import time
import sqlite3
from siricoin import siriCoin
from dotenv import dotenv_values
from flask_hcaptcha import hCaptcha
from flask import Flask, request, render_template

faucetaddress = "0x7185Df2872435b0cCf6abDd0019886b6CF7d76A7"
privkey = dotenv_values(".env")["PRIVATE_KEY"]

con = sqlite3.connect("./users.db")
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users(address string, ip string, time int)")
con.commit()
con.close()

app = Flask(__name__)
hcaptcha = hCaptcha(app, site_key="b5d4f8a3-6700-4d93-a23b-ba1e2a230f63", secret_key="0x4f5de13bB30963Df26f3E639E7272277C9253a79", is_enabled=True)

@app.route("/")
def index():
    return render_template("index.html", hcaptcha=hcaptcha.get_code())

@app.route("/claim", methods=["POST"])
def claim():
    if hcaptcha.verify():
        address = request.form.get("address")
        siri = siriCoin()
        if not siri.is_address(address):
            return "This is not an valid address."

        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        con = sqlite3.connect("./users.db")
        cur = con.cursor()

        lastclaim = cur.execute("SELECT time FROM users WHERE ip = (?) OR address = (?) ORDER BY time DESC", (ip, address,))

        lastclaim = lastclaim.fetchone()

        print(lastclaim)

        over = time.time()

        if lastclaim == None:
            noclaim = True
        elif int(lastclaim[0]) + 21600 < over:
            noclaim = False
        else:
            overread = int(lastclaim[0]) + 21600
            overread = time.strftime("%D %H:%M", time.localtime(overread))
            return f"No, you already claimed the faucet. Come back at {overread}"

        bal = siri.balance(address)
        if bal >=1000: #250
            return "You're too rich. Come back when you lost all your money gambling. ;)"
        
        bal = siri.balance(faucetaddress)
        if bal <= 7:
            return "Faucet balance too low, no money for now."
        amount = 0.075
        try:
            tx = siri.transaction(privkey, faucetaddress, address, amount)
        except:
            return "An unknown error occured. Try again."

        if tx == None:
            return "An unknown error occured. Try again."

        if noclaim == True:
            cur.execute("INSERT INTO users VALUES (?, ?, ?)", (address, ip, int(time.time()),))

        else:
            cur.execute("UPDATE users SET time = (?), ip = (?) WHERE address = (?)", (int(time.time()), ip, address,))

        con.commit()
        con.close()

        return f"Oki, txid: {tx}"
    else:
        return "Solve the captcha first!"


if __name__ == "__main__":
    app.run()
