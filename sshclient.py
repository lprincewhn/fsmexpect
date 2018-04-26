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

class PasswordError(Exception):
    pass

class ConnectionError(Exception):
    pass

class Timeout(Exception):
    pass

class SCPHandler:

    def __init__(self, ip, loginUser, loginPass):
        self.ip = ip
        self.loginUser = loginUser
        self.loginPass = loginPass

    def upload(self, localFile, remoteFile, timeout=30):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s %s@%s:%s' % (localFile, self.loginUser, self.ip, remoteFile)
        logger.debug(scp_cmd)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return
        scp = pexpect.spawn(scp_cmd)
        try:
            scp.expect(['assword:'], timeout)
        except pexpect.EOF:
            logger.warning("SCP Connection Fail")
            scp.close()
            raise ConnectionError("SCP Connection Fail")
        except pexpect.TIMEOUT:
            logger.warning("SCP Connection TIMEOUT")
            scp.close()
            raise Timeout("SCP connection timeout!")
        logger.debug('Send login password.')
        scp.sendline(self.loginPass)
        try:
            i = scp.expect(['100%', 'assword: '], timeout)
            logger.debug('Upload %s successfully.' % (localFile))
            scp.close()
            if i != 0:
                raise PasswordError('Wrong Password!')
        except pexpect.TIMEOUT:
            raise Timeout('SCP upload timeout!')

    def download(self, remoteFile, localFile, timeout=30):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s@%s:%s %s' % (self.loginUser, self.ip, remoteFile, localFile)
        logger.debug(scp_cmd)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return
        scp = pexpect.spawn(scp_cmd)
        try:
            scp.expect(['assword:'], timeout)
        except pexpect.EOF:
            logger.warning("SCP Connection Fail")
            scp.close()
            raise ConnectionError("SCP Connection Fail")
        except pexpect.TIMEOUT:
            logger.warning("SCP Connection TIMEOUT")
            scp.close()
            raise Timeout("SCP connection timeout!")
        logger.debug('Send login password.')
        scp.sendline(self.loginPass)
        try:
            i = scp.expect(['100%', 'assword: '], timeout)
            logger.debug('Download %s successfully.' % (localFile))
            scp.close()
            if i != 0:
                raise PasswordError('Wrong Password!')
        except pexpect.TIMEOUT:
            raise Timeout('SCP download timeout!')

class SSHHandler:

    def __init__(self, ip, loginUser, loginPass, prompt, timeout=10):
        ssh_cmd = 'ssh -o StrictHostKeyChecking=no %s@%s' % (loginUser, ip)
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            self.user = loginUser
            return
        self.ssh = pexpect.spawn(ssh_cmd)
        try:
            self.ssh.expect(['assword:'], timeout)
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
                raise PasswordError('Wrong Password!')
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
                raise PasswordError('Wrong Password!')
        except pexpect.TIMEOUT:
            raise Timeout('Command timeout!')

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
            except:
                raise Timeout('Command timeout!')
        if prompt:
            self.prompt = prompt
        return result


    def close(self):
        """
        Close the ssh session.
        """

        logger.debug('Close ssh session.')
        if not PEXPECT:
            logger.warning('Pexpect is not supported.')
            return

        self.ssh.close()


