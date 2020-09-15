import sys, os, re

flags = { 
    'redirected': False,
    'piped': False,
    'cd': False,
    'direction': '',
    'output': False,
    'fd': None,
    'copyFd': None,
    'fileFlags': None
}

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
        except FileNotFoundError:
            pass
    os.write(2, ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1) 

def redirect(paths, cmd, args):
    os.close(flags['fd'])
    os.open(flags['direction'], flags['fileFlags'])
    os.set_inheritable(flags['copyFd'], True)
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
        except FileNotFoundError:
            pass
    os.write(2, ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1)

def validateInput(line):
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
                flags['output'] = True         
                flags['fd'] = 1 
                flags['copyFd'] = os.dup(flags['fd'])
                flags['fileFlags'] = os.O_CREAT | os.O_WRONLY
            else: 
                dirIndex = line.index('<')
                flags['output'] = False         
                flags['fd'] = 0 
                flags['copyFd'] = os.dup(flags['fd'])
                flags['fileFlags'] = os.O_RDONLY
            flags['direction'] = line[dirIndex+1]
            line = line[0:dirIndex]
        elif line[1] == '|':
            flags['piped'] = True

    path, cmd = getCmd(line[0])
    args = [cmd] + line[1:]
    paths = [path] if path != None else re.split(':', os.environ['PATH'])
    return paths, cmd, args
    
pid = os.getpid()
line = re.split(' ', prompt()[0:-1])

while True:    
    paths, cmd, args = validateInput(line)

    if flags['cd']:
        os.chdir(paths[0])
        flags['cd'] = False
    else:
        rc = os.fork()

        if rc < 0:
            os.write(2, ('fork failed, returning {}\n'.format(rc).encode()))
            sys.exit(1)
        elif rc == 0:
            if flags['redirected']:
                redirect(paths, cmd, args)
            else:
                normal(paths, cmd, args)
        else:
            childPidCode = os.wait()
            if flags['redirected']:
                os.dup2(flags['copyFd'], flags['fd'])
                os.close(flags['copyFd']) 
                flags['redirected'] = False
            if childPidCode[1] != 0:
                os.write(1, ('Program terminated with exit code {}\n'.format(childPidCode[1])).encode())
    line = re.split(' ', prompt()[0:-1])
