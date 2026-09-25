"""Package-wide constants for LSP-dita."""

PACKAGE_NAME = "LSP-dita"
SESSION_NAME = "dita"
SETTINGS_FILE = "LSP-dita.sublime-settings"

SERVER_VERSION = "0.1.0"
JAR_NAME = "dita-language-server-{}-all.jar".format(SERVER_VERSION)
JAR_URL = (
    "https://github.com/aireilly/dita-language-server/releases/download/"
    "v{}/{}".format(SERVER_VERSION, JAR_NAME)
)
JAR_SHA256 = "e865acc51053b4158a4d7b200e97756433cb0477855f4476082489175f9d078c"

MINIMUM_JAVA = 17

SYNTAX_SCOPE = "text.xml.dita"
