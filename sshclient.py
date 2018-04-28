#!/usr/bin/python
#coding=utf8

import sys

try:
    import pexpect
    PEXPECT = True
except:
    PEXPECT = False

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
            return False, scp.exitstatus

    def upload(self, localFile, remoteFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s %s@%s:%s' % (localFile, self.loginUser, self.ip, remoteFile)
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %d" %(exitstatus))


    def download(self, remoteFile, localFile):
        scp_cmd = 'scp -o StrictHostKeyChecking=no %s@%s:%s %s' % (self.loginUser, self.ip, remoteFile, localFile)
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp)
        if need_pass:
            raise AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise SCPFailed("Upload failed. Exit code: %d" %(exitstatus))

class Action:

    def __init__(self, action_type, action_value = None, output_on = True):
        self.action_type = action_type
        self.expects = []
        self.nexts  = []
        self.output_on = output_on
        if action_type == 'command' or action_type == 'continue':
            self.command = action_value
        if action_type == 'exception':
            self.exception = action_value
        if action_type == 'end':
            self.end_callback = action_value

    def add_next_action(self, expect_str, action):
        self.expects.append(expect_str)
        self.nexts.append(action)

class SSHHandler:

    def __init__(self, ip, loginUser, prompt, loginPass='', timeout=10):
        ssh_cmd = 'ssh -o StrictHostKeyChecking=no %s@%s' % (loginUser, ip)
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

        pass_action = Action("command", loginPass, False)
        def callback():
            self.prompt = prompt
            self.user = loginUser
        succ_action = Action("end", callback)
        fail_action = Action("exception", AuthenticationFailed())
        pass_action.add_next_action('.+assword: ', fail_action)
        pass_action.add_next_action(prompt, succ_action)
        self.start_action(pass_action)

    def start_action(self, action, timeout=10):
        current =  action
        output = ''
        while True:
            if current.action_type in ["command", "continue"] :
                self.ssh.sendline(current.command)
                if current.action_type == "command":
                    self.ssh.readline()
                try:
                    i = self.ssh.expect(current.expects, timeout)
                    if current.output_on:
                        output += self.ssh.before
                    current = current.nexts[i]
                except pexpect.TIMEOUT:
                    raise Timeout('Command timeout!')
                except pexpect.EOF:
                    return ssh.exitstatus
            elif current.action_type == "exception":
                raise current.exception
            elif current.action_type == "end":
                if current.end_callback:
                    current.end_callback()
                break
        return output

    def change_prompt(self, cmd, prompt, password='', timeout=10):
        cmd_action = Action("command", cmd)
        def callback():
            self.prompt = prompt
        succ_action = Action("end", callback)
        pass_action = Action("command", password)

        cmd_action.add_next_action('.+assword:', pass_action) # Need password
        cmd_action.add_next_action(prompt, succ_action)  # Success directly
        pass_action.add_next_action(prompt, succ_action)  # Success
        pass_action.add_next_action("Authentication failure", Action("exception", AuthenticationFailed()))   # Wrong password
        self.start_action(cmd_action, timeout)

    def run_cmd(self, cmd, out=sys.stdout, password='', timeout=10):
        cmd_action = Action("command", cmd)
        succ_action = Action("end")
        pass_action = Action("command", password)
        continue_action = Action("continue", " ")

        cmd_action.add_next_action(self.prompt, succ_action)      # Success directly
        cmd_action.add_next_action('.+assword:', pass_action)  # Need password
        cmd_action.add_next_action('--More--\(\d+%\)', continue_action) # Long output
        pass_action.add_next_action(self.prompt, succ_action)  # Success directly
        pass_action.add_next_action("Authentication failure", Action("exception", AuthenticationFailed())) # Wrong password
        pass_action.add_next_action('--More--\(\d+%\)', continue_action) # Long output
        continue_action.add_next_action(self.prompt, succ_action)
        continue_action.add_next_action('--More--\(\d+%\)', continue_action)
        output = self.start_action(cmd_action, timeout)
        out.write(output)
        return output

    def close(self):
        self.ssh.close()

