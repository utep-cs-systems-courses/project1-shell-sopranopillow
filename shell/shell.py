import sys, os, re

def prompt():
    os.write(1, ('$ '.encode()))
    sys.stdout.flush()
    cmd = os.read(1, 10000)
    return cmd.decode('utf-8')

def getCmd(str):
    pth = re.search('/.*/', str)
    pth = None if pth == None else pth.group()
    cmd = str if pth == None else str.replace(pth, '')
    return pth, cmd

def normal(paths, cmd, args):
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
            sys.stdout.flush()
        except FileNotFoundError:
            pass
    os.write(2, ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1) 

def redirect(paths, cmd, args, direction):
    os.close(1)
    os.open(direction, os.O_CREAT | os.O_WRONLY)
    os.set_inheritable(1, True)
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
            sys.stdout.flush()
        except FileNotFoundError:
            pass
    os.write(2, ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1)

if __name__ == "__main__":
    pid = os.getpid()

    while True:
        rc = os.fork()

        if rc < 0:
            os.write(2, ('fork failed, returning {}\n'.format(rc).encode()))
            sys.exit(1)
        elif rc == 0:
            splitLine = re.split(' ', prompt()[0:-1])
            redirected = piped = False
            direction = ""
            if len(splitLine) >= 3:
                if splitLine[1] == ">":
                    redirected = True
                    direction = splitLine[2]
                    splitLine = [splitLine[0]] + (splitLine[3:] if len(splitLine) > 3 else [])
                elif splitLine[1] == "|":
                    piped = True
                    splitLine = [splitLine[0]] + splitLine[2:]
                
            path, cmd = getCmd(splitLine[0])
            args = [cmd] + splitLine[1:]
            paths = [path] if path != None else re.split(':', os.environ['PATH'])
            #if piped:
            #    piped(paths, cmd, args)
            if redirected:
                redirect(paths, cmd, args, direction)
            else:
                normal(paths, cmd, args)
        else:
            childPidCode = os.wait()
