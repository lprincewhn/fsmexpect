#!/usr/bin/python
#coding=utf8

import sys
import pexpect

debug = False
logger = None

def _debug(str):
    if logger:
        logger.debug(str)
    elif debug:
        print str

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
            scp.expect(['.+assword:'])
            return True, None
        except pexpect.EOF:
            _debug("SCP exit with %s" % (scp.exitstatus))
            return False, scp.exitstatus

    def upload(self, localFile, remoteFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s %s@%s:%s' % (localFile, self.loginUser, self.ip, remoteFile)
        _debug("Start SCP upload：%s" % (scp_cmd))
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %s" %(exitstatus))


    def download(self, remoteFile, localFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s@%s:%s %s' % (self.loginUser, self.ip, remoteFile, localFile)
        _debug("Start SCP download：%s" % (scp_cmd))
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %s" %(exitstatus))

class FSMState:

    def __init__(self, state_type, action = None, output_on = True):
        self.state_type = state_type
        self.expects = []
        self.nexts  = []
        self.output_on = output_on
        if state_type == 'command' or state_type == 'operate':
            self.command = action
        if state_type == 'exception':
            self.exception = action
        if state_type == 'end':
            self.end_callback = action

    def add_next_state(self, expect_str, state):
        self.expects.append(expect_str)
        self.nexts.append(state)

    def start(self, p_expect, timeout=10):
        current = self
        output = ''
        while True:
            if current.state_type in ["command", "operate"] :
                p_expect.sendline(current.command)
                _debug("Send：%s" % (current.command))
                if current.state_type == "command":
                    p_expect.readline()
                try:
                    i = p_expect.expect(current.expects, timeout)
                    if current.output_on:
                        output += p_expect.before
                    current = current.nexts[i]
                except pexpect.TIMEOUT:
                    raise Timeout('Command timeout!')
                except pexpect.EOF:
                    return p_expect.exitstatus
            elif current.state_type == "exception":
                raise current.exception
            elif current.state_type == "end":
                if current.end_callback:
                    current.end_callback()
                break
        return output

class SSHHandler:

    def __init__(self, ip, loginUser, prompt, loginPass='', timeout=10):
        ssh_cmd = 'ssh -o StrictHostKeyChecking=no %s@%s' % (loginUser, ip)
        _debug("Start ssh: %s" % (ssh_cmd))
        self.ssh = pexpect.spawn(ssh_cmd)
        try:
            i = self.ssh.expect([prompt, '.+assword:'], timeout)
            if i == 0:
                self.prompt = prompt
                self.user = loginUser
                return
        except pexpect.EOF:
            self.ssh.close()
            raise ConnectionError()
        except pexpect.TIMEOUT:
            self.ssh.close()
            raise Timeout("SSH connection timeout!")

        pass_state = FSMState("command", loginPass, False)
        def callback():
            self.prompt = prompt
            self.user = loginUser
        succ_state = FSMState("end", callback)
        fail_state = FSMState("exception", AuthenticationFailed())
        pass_state.add_next_state('.+assword: ', fail_state)
        pass_state.add_next_state(prompt, succ_state)
        pass_state.start(self.ssh)

    def p_expect(self):
        return self.ssh

    def change_prompt(self, cmd, prompt, password='', timeout=10):
        _debug("Run %s and change prompt to %s" % (cmd, prompt))
        cmd_state = FSMState("command", cmd)
        def callback():
            self.prompt = prompt
        succ_state = FSMState("end", callback)
        pass_state = FSMState("command", password)
        fail_state = FSMState("exception", AuthenticationFailed())

        cmd_state.add_next_state('.+assword:', pass_state)                 # Need password
        cmd_state.add_next_state(prompt, succ_state)                       # Success directly
        pass_state.add_next_state(prompt, succ_state)                      # Success
        pass_state.add_next_state("Authentication failure", fail_state)    # Wrong password
        cmd_state.start(self.ssh, timeout)

    def run_cmd(self, cmd, out=sys.stdout, password='', timeout=10):
        _debug("Run %s" % (cmd))
        cmd_state = FSMState("command", cmd)
        succ_state= FSMState("end")
        pass_state = FSMState("command", password)
        fail_state = FSMState("exception", AuthenticationFailed())
        continue_state = FSMState("operate", " ")

        cmd_state.add_next_state(self.prompt, succ_state)                  # Success directly
        cmd_state.add_next_state('.+assword:', pass_state)                 # Need password
        cmd_state.add_next_state('--More--\(\d+%\)', continue_state)       # Long output
        pass_state.add_next_state(self.prompt, succ_state)                 # Success directly
        pass_state.add_next_state("Authentication failure", fail_state)    # Wrong password
        pass_state.add_next_state('--More--\(\d+%\)', continue_state)      # Long output
        continue_state.add_next_state(self.prompt, succ_state)
        continue_state.add_next_state('--More--\(\d+%\)', continue_state)
        output = cmd_state.start(self.ssh, timeout)
        out.write(output)
        return output

    def close(self):
        _debug("Close ssh.")
        self.ssh.close()
