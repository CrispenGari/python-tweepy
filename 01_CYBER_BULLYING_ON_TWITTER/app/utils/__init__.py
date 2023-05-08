import re

is_valid_email = lambda email: re.match(
    r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", email
)

is_valid_password = lambda password: len(password.strip()) >= 5
