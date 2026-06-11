from environs import Env

env = Env()
env.read_env()

TOKEN = env.str("TOKEN")
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
ADMIN_CHAT_ID = env.int("ADMIN_CHAT_ID")

DB_NAME = env.str("DB_NAME")
DB_USER = env.str("DB_USER")
DB_PASSWORD = env.str("DB_PASSWORD")
DB_HOST = env.str("DB_HOST")
DB_PORT = env.int("DB_PORT")
