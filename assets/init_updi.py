Import("env")

try:
    # check if pymcuprog is installed
    import pymcuprog
except ImportError:
    # install pymcuprog
    env.Execute("$PYTHONEXE -m pip install pymcuprog")

# get the target board
boardMCU = env["BOARD_MCU"]

# append the default build flags
env.Append( 
    UPDI_FLAGS= [
        "write",
        "--device",
        boardMCU,
        "--tool",
        "uart",
        "--verify",
        "--erase",
        "--timing",
    ]
)

