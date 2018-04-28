#!/usr/bin/env python
#encoding: utf-8

import unittest
import sshclient
import sys
import StringIO

class TestSSHHandler(unittest.TestCase):

    def setUp(self):
        self.outfile = StringIO.StringIO()
        self.host = '192.168.56.8'
        self.userwithpass = 'vagrant'
        self.userwithoutpass = 'root'
        self.userpass = 'vagrant'

    def tearDown(self):
        pass

    def testNoPasswordInteract(self):
        prompt = '\[root@devtest ~\]# '
        ssh = sshclient.SSHHandler(self.host, self.userwithoutpass, prompt)
        endAction = sshclient.Action("end")
        lsAction = sshclient.Action("command", "ls")
        lsAction.add_next_action('\[vagrant@devtest ~\]\$', endAction)
        suAction = sshclient.Action("command", "su - vagrant", False)
        suAction.add_next_action('\[vagrant@devtest ~\]\$', lsAction)
        result = suAction.start(ssh.ssh)
        ssh.close()

    def testPasswordInteract(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = sshclient.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        endAction = sshclient.Action("end")
        lsAction = sshclient.Action("command", "ls")
        lsAction.add_next_action('\[root@devtest ~\]#', endAction)
        wpAction = sshclient.Action("exception")
        wpAction.exception = sshclient.AuthenticationFailed()
        passAction = sshclient.Action("command", "vagrant", False)
        passAction.add_next_action('\[root@devtest ~\]#', lsAction)
        passAction.add_next_action('Authentication failure', wpAction)
        suAction = sshclient.Action("command", "su - ", False)
        suAction.add_next_action('assword:', passAction)
        result = suAction.start(ssh.ssh)
        ssh.close()

if __name__ == '__main__':
    unittest.main()
