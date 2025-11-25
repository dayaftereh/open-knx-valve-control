Import("env")

# check if a port is configured
port = env.get("UPLOAD_PORT")

# check if a port is found
if port is None:
    # if not auto-detected port
    env.AutodetectUploadPort()
    # get the found port
    port = env.get("UPLOAD_PORT")
    # set the port to monitor port
    env.Append( 
       MONITOR_PORT = port,
    )