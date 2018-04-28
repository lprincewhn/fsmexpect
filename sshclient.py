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

    def __init__(self, action_type, expects, nexts, output = True):
        self.action_type = action_type
        self.expects = expects
        self.nexts  = nexts
        self.output = output
        
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

        self.ssh.sendline('su - %s' % (newUser))
        if self.user != "root":
            i = self.ssh.expect(['assword:'])
            if i == 0:
                self.ssh.sendline(newPass)
                self.ssh.expect('\n')
        try:
            i = self.ssh.expect([prompt, 'Sorry'], min(timeout, 10))
            if i == 0:
                self.prompt = prompt
                self.user = newUser
            else:
                raise AuthenticationFailed('Authentication failed.')
        except pexpect.TIMEOUT:
            raise Timeout('Command timeout!')

    def interacts(self, first, out=sys.stdout, timeout=10):
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            out.write('Command Fail. Error: Pexpect is not supported.')
            return
        action = first
        while True:
            if action.action_type == "command":
                self.ssh.sendline(action.command) 
                print action.command
                self.ssh.readline()
                i = self.ssh.expect(action.expects, timeout)
                if action.output:
                    out.write(self.ssh.before)
                action = action.nexts[i]
            elif action.action_type == "exception":
                raise action.exception
            elif action.action_type == "end":
                break
        
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

