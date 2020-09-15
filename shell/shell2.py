#! /usr/bin/env python3

import sys, os, re

flags = {
    'redirected': False,
    'redirection': '',
    'output': False,
    'cd': False,
}

fileDescriptors = {
    'stdin': 0,
    'stdout': 1,
    'stderr': 2,
    'stdcopy': None,
    'stdprev': None
}

def prompt():
    ps1 = '$ '
    try: # needed to run inside emacs
        ps1 = ps1 if os.environ['PS1'] == '' else os.environ['PS1']
    except Exception:
        pass

    os.write(fileDescriptors['stdout'], (ps1).encode())
    cmd = os.read(fileDescriptors['stdin'], 1000).decode()
    return cmd if cmd[-1] != '\n' else cmd[:-1]

def execCmd(paths, cmd, args):
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
        except FileNotFoundError:
            pass
    os.write(fileDescriptors['stderr'], ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1)

def setFlags(line):
    if len(line) == 1:
        if line[0] == 'exit':
            sys.exit(0)
    if line [0] == 'cd':
        flags['cd'] = True
    if len(line) >= 3:
        if '>' in line or '<' in line:
            flags['redirected'] = True
            if '>' in line:
                dirIndex = line.index('>')
                flags['output'] = True
                fileDescriptors['stdprev'] = 1
                fileDescriptors['stdcopy'] = os.dup(1)
            else:
                dirIndex = line.index('<')
                flags['output'] = False
                fileDescriptors['stdprev'] = 0
                fileDescriptors['stdcopy'] = os.dup(0)
            flags['redirection'] = line[dirIndex+1]
            line = line[:dirIndex]
            os.close(fileDescriptors['stdprev'])
            os.open(flags['redirection'], (os.O_CREAT | os.O_WRONLY) if flags['output'] else os.O_RDONLY)
            os.set_inheritable(fileDescriptors['stdprev'], True)
    return line

def getCommand(line):
    cmdPath = re.search('/.*/', line[0])
    cmdPath = None if cmdPath == None else cmdPath.group()
    cmd = line[0] if cmdPath == None else line[0].replace(cmdPath, '')
    args = [cmd] + line[1:]
    paths = [cmdPath] if cmdPath != None else re.split(':', os.environ['PATH'])
    return paths, cmd, args


### main
pid = os.getpid()
line = re.split(' ', prompt())

while True:
    line = setFlags(line)
    paths, cmd, args = getCommand(line)

    if cmd == 'cd':
        os.chdir(args[1])
        flags['cd'] = False
    else:
        rc = os.fork()

        if rc < 0:
            os.write(fileDescriptors['stderr'], ('fork failed, returning {}\n'.format(rc).encode()))
            sys.exit(1)
        elif rc == 0:
            execCmd(paths, cmd, args)
        else:
            childPidCode = os.wait()
            if flags['redirected']:
                os.dup2(fileDescriptors['stdcopy'], fileDescriptors['stdprev'])
                os.close(fileDescriptors['stdcopy'])
                flags['redirected'] = False
            if childPidCode[1] != 0:
                os.write(fileDescriptors['stdout'], ('Program terminated with exit code {}\n'.format(childPidCode[1])).encode())
    line = re.split(' ', prompt())
