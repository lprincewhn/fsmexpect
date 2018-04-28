#!/usr/bin/python
#coding=utf8

import sys
import logging

try:
    import pexpect
    PEXPECT = True
except:
    PEXPECT = False

logger = logging.getLogger("SSHClient")

class AuthenticationFailed(Exception):
    pass

class ConnectionError(Exception):
    pass

class Timeout(Exception):
    pass

class SCPFailed(Exception):
    pass

class SCPHandler:

    def __init__(self, ip, loginUser, loginPass=''):
        self.ip = ip
        self.loginUser = loginUser
        self.loginPass = loginPass

    def need_pass(self,scp):
        try:
            scp.expect(['assword:'])
            return True, None
        except pexpect.EOF:
            return False, scp.exitstatus

    def upload(self, localFile, remoteFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s %s@%s:%s' % (localFile, self.loginUser, self.ip, remoteFile)
        logger.debug(scp_cmd)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            logger.debug('Send login password.')
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %d" %(exitstatus))  
            else:
                logger.debug("Successful to upload file %s" %(localFile)) 
        

    def download(self, remoteFile, localFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s@%s:%s %s' % (self.loginUser, self.ip, remoteFile, localFile)
        logger.debug(scp_cmd)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            logger.debug('Send login password.')
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %d" %(exitstatus))
            else:
                logger.debug("Successful to download file %s" %(localFile))

class Action:

    def __init__(self, action_type, action_value = None, output = True):
        self.action_type = action_type
        self.expects = []
        self.nexts  = [] 
        self.output = output
        if action_type == 'command':
            self.command = action_value
        if action_type == 'exception':
            self.exception = action_value
        if action_type == 'end':
            self.end_callback = action_value

    def add_next_action(self, expect_str, action):
        self.expects.append(expect_str)
        self.nexts.append(action)

    def start(self, progress, out=sys.stdout, timeout=10):
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            out.write('Command Fail. Error: Pexpect is not supported.')
            return
        action = self 
        while True:
            if action.action_type == "command":
                print action.command
                progress.sendline(action.command) 
                progress.readline()
                try:
                    i = progress.expect(action.expects, timeout)
                    if action.output:
                        out.write(progress.before)
                    action = action.nexts[i]
                except pexpect.TIMEOUT:
                    raise Timeout('Command timeout!')
                except pexpect.EOF:
                    return ssh.exitstatus
            elif action.action_type == "exception":
                raise action.exception
            elif action.action_type == "end":
                if action.end_callback:
                    action.end_callback()
                break

class SSHHandler:

    def __init__(self, ip, loginUser, prompt, loginPass='', timeout=10):
        ssh_cmd = 'ssh -o StrictHostKeyChecking=no %s@%s' % (loginUser, ip)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            self.user = loginUser
            return
        self.ssh = pexpect.spawn(ssh_cmd)
        try:
            i = self.ssh.expect([prompt, 'assword:'], timeout)
            if i == 0:
                self.prompt = prompt
                self.user = loginUser
                return
        except pexpect.EOF:
            logger.warning("SSH Connection Fail")
            self.ssh.close()
            raise ConnectionError()
        except pexpect.TIMEOUT:
            logger.warning("SSH Connection TIMEOUT")
            self.ssh.close()
            raise Timeout("SSH connection timeout!")

        logger.debug('Send login password.')
        self.ssh.sendline(loginPass)
        try:
            i = self.ssh.expect([prompt, 'assword: '], timeout)
            if i == 0:
                self.prompt = prompt
                self.user = loginUser
            else:
                self.ssh.close()
                raise AuthenticationFailed('Authentication failed!')
        except pexpect.TIMEOUT:
            raise Timeout('Login timeout!')

    def changeUser(self, newUser, newPass, prompt, timeout=10):
        logger.debug('Change user to %s' % (newUser))
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            self.user = newUser
            return
        suAction = Action("command", 'su - %s' % (newUser), False)
        def callback():
            self.prompt = prompt
        succAction = Action("end", callback)
        if self.user != "root":
            passAction = Action("command", newPass)
            suAction.add_next_action('assword:', passAction)
            passAction.add_next_action(prompt, succAction)
            passAction.add_next_action("Authentication failure", Action("exception", AuthenticationFailed()))
        else: 
            suAction.add_next_action(prompt, succAction)       
        suAction.start(self.ssh)

    def runCommand(self, cmd, out=sys.stdout, prompt=None, timeout=10):
        logger.debug('Run Command: %s.' % (cmd))
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            out.write('Command Fail. Error: Pexpect is not supported.')
            return

        self.ssh.sendline(cmd)
        self.ssh.readline()
        if prompt is None:
            prompt_w = self.prompt
        else:
            prompt_w = prompt
        i = -1
        result = ""
        while i != 0:
            try:
                i = self.ssh.expect([prompt_w, "--More--"], timeout)
                out.write(self.ssh.before)
                result += self.ssh.before
                if i == 1:
                    self.ssh.send(" ")
            except pexpect.TIMEOUT:
                raise Timeout('Command timeout!')
        if prompt:
            self.prompt = prompt
        return result


    def close(self):
        logger.debug('Close ssh session.')
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return

        self.ssh.close()

if __name__  == '__main__':
    prompt = '\[vagrant@devtest ~\]\$ '
    ssh = SSHHandler('localhost', 'vagrant', prompt, 'vagrant')
    ssh.changeUser('root', 'vagrant', '\[root@devtest ~\]# ')
    ssh.runCommand("ls")
    ssh.close()
