import sys, os, re

def prompt():
    os.write(1, '{} $ '.format(os.getcwd().replace(os.environ['HOME'], '')).encode())
    sys.stdout.flush()
    cmd = os.read(1, 10000)
    return cmd.decode('utf-8')

def getCmd(str):
    pth = re.search('/.*/', str)
    pth = None if pth == None else pth.group()
    cmd = str if pth == None else str.replace(pth, '')
    return pth, cmd

if __name__ == "__main__":
    pid = os.getpid()

    while True:
        rc = os.fork()

        if rc < 0:
            os.write(2, ('fork failed, returning {}\n'.format(rc).encode()))
            sys.exit(1)
        elif rc == 0:
            line = prompt().replace('\n', '')
            splitLine = re.split(' ', line)
            path, cmd = getCmd(splitLine[0])
            args = splitLine[1:]
            paths = [path] if path != None else re.split(':', os.environ['PATH'])
            for p in paths:
                try:
                    os.execve('{}/{}'.format(p, cmd), args, os.environ)
                    sys.stdout.flush()
                except FileNotFoundError:
                    pass
            os.write(2, ('could not execute: {}\n'.format(cmd)).encode())
            sys.exit(1)
        else:
            childPidCode = os.wait()
