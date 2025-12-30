from pwdlib import PasswordHash 

password_hasher = PasswordHash.recommended()

def get_password_hash(password):
    return password_hasher.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hasher.verify(plain_password, hashed_password)

