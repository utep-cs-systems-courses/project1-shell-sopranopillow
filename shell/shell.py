#! /usr/bin/env python3
import sys, os, re

flags = { # Flags to setup filedescriptors before command
    'redirected': False,
    'redirection': '',
    'output': False,
    'cd': False,
    'piped': False,
    'pr': None,
    'pw': None,
    'background': False,
}

cmdQ = []

fileDescriptors = {
    'stdin': 0,
    'stdout': 1,
    'stderr': 2,
    'stdcopy': None,
    'stdprev': None
}

def prompt():
    ps1 = '$ '
    try: # needed to work in console inside emacs
        ps1 = ps1 if os.environ['PS1'] == '' else os.environ['PS1']
    except Exception:
        pass
    os.write(fileDescriptors['stdout'], (ps1).encode()) # writing prompt
    cmd = os.read(fileDescriptors['stdin'], 1000).decode() # getting input
    return cmd[:-1] if cmd[-1] == '\n' else cmd

def execCmd(paths, cmd, args): # executes command, assumes setup has been done
    for p in paths:
        try:
            os.execve('{}/{}'.format(p, cmd), args, os.environ)
        except FileNotFoundError:
            pass
    os.write(fileDescriptors['stderr'], ('{}: command not found\n'.format(cmd)).encode())
    sys.exit(1)

def setFlags(line): # sets flags and sets up to execute command
    if len(line) == 1:
        if line[0] == 'exit':
            sys.exit(0)
    if line [0] == 'cd':
        flags['cd'] = True
    if '&' in line:
        flags['background'] = True
        line.remove('&')
    if len(line) >= 3:
        if '|' in line:
            flags['piped'] = True
            flags['pr'], flags['pw'] = os.pipe()
            for f in (flags['pr'], flags['pw']):
                os.set_inheritable(f, True)
            os.close(1)
            os.dup(flags['pw'])

        elif '>' in line or '<' in line:
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

def getCommand(line): # splits command and sets up paths, command, and arguments
    cmdPath = re.search('/.*/', line[0])
    cmdPath = None if cmdPath == None else cmdPath.group()
    cmd = line[0] if cmdPath == None else line[0].replace(cmdPath, '')
    args = [cmd] + line[1:]
    paths = [cmdPath] if cmdPath != None else re.split(':', os.environ['PATH'])
    return paths, cmd, args
    
def checkLine(line):
    cmds = []
    l = line.split('\\n')
    if len(l) == 1:
        return l
    for i in l:
        if i != '':
            cmds.append(i)
    return cmds[-1::-1] # reversing list so it executes from first to last

### main
pid = os.getpid()

while True:
    if len(cmdQ) == 0:
        line = prompt()
        line = checkLine(line)
        if len(line) == 1:
            line = line[0]
        else:
            cmdQ = line
            line = cmdQ.pop()
    else:
        line = cmdQ.pop()
    line = line if line[0] != ' ' else line[1:] #removing white space in case they were adeded
    line = line if line[-1] != ' ' else line[:-1]
    line = re.split(' ', line)
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
            if not flags['background']:
                childPidCode = os.wait()
                flags['background'] = True
            if flags['redirected']:
                os.dup2(fileDescriptors['stdcopy'], fileDescriptors['stdprev']) # restoring and closing file descriptors
                os.close(fileDescriptors['stdcopy'])
                flags['redirected'] = False
            if flags['piped']:
                for fd in (flags['pr'], flags['pw']):
                    os.close(fd)
                flags['piped'] = False
            if not flags['background'] and childPidCode[1] != 0:
                os.write(fileDescriptors['stdout'], ('Program terminated with exit code {}\n'.format(childPidCode[1])).encode())
