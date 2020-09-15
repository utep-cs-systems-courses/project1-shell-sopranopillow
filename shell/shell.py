import sys, os, re

def prompt():
    ps1 = '$ '
    try: # This is needed if you want to use the shell inside emacs
        ps1 = ps1 if os.environ['PS1'] == '' else '{}'.format(os.environ["PS1"])
    except Exception:
        pass

    os.write(1, ('{}'.format(ps1).encode()))
    sys.stdout.flush()
    cmd = os.read(0, 1000)
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

def redirect(paths, cmd, args, flags):
    os.close(flags['fd'])
    os.open(flags['direction'], os.O_CREAT | os.O_WRONLY)
    os.set_inheritable(flags['copyFd'], True)
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
        except FileNotFoundError:
            pass
    os.write(2, ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1)

def validateInput(line, flags):
    if len(line) == 1:
        if line[0] == 'exit':
            sys.exit(0)
    if line[0] == 'cd':
            flags['cd'] = True
            return [line[1]], None, None
    if len(line) >= 3:
        if '>' in line or '<' in line:
            flags['redirected'] = True
            if '>' in line:
                dirIndex = line.index('>')
            else:
                dirIndex = line.index('<')
            flags['direction'] = line[dirIndex+1]
            flags['output'] = True if '>' in line else False
            line = line[0:dirIndex]
            flags['fd'] = 1 if flags['output'] else 0
            flags['copyFd'] = os.dup(flags['fd'])
        elif line[1] == '|':
            flags['piped'] = True

    path, cmd = getCmd(line[0])
    args = [cmd] + line[1:]
    paths = [path] if path != None else re.split(':', os.environ['PATH'])
    #if flags['piped']:
    #    piped(paths, cmd, args)
    return paths, cmd, args
    
if __name__ == '__main__':
    pid = os.getpid()
    flags = { 
        'redirected': False,
        'piped': False,
        'cd': False,
        'direction': '',
        'output': False,
        'copyFd': None,
        'fd': None
    } 
    line = re.split(' ', prompt()[0:-1])
    
    while True:    
        paths, cmd, args = validateInput(line, flags)

        if flags['cd']:
            os.chdir(paths[0])
        else:
            rc = os.fork()

            if rc < 0:
                os.write(2, ('fork failed, returning {}\n'.format(rc).encode()))
                sys.exit(1)
            elif rc == 0:
                if flags['redirected']:
                    redirect(paths, cmd, args, flags)
                else:
                    normal(paths, cmd, args)
            else:
                childPidCode = os.wait()
                if flags['redirected']:
                    print(flags)
                    os.dup2(flags['copyFd'], flags['fd'])
                    os.close(flags['copyFd'])

                flags = {
                    'redirected': False,
                    'piped': False,
                    'cd': False,
                    'direction': '',
                    'output': False,
                    'copyFd': None,
                    'fd': None
                } 
                if childPidCode[1] != 0:
                    os.write(1, ('Program terminated with exit code {}\n'.format(childPidCode[1])).encode())
        line = re.split(' ', prompt()[0:-1])
