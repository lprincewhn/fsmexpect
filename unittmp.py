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
        endAction = sshclient.Action("end", [], [])
        lsAction = sshclient.Action("command", ['\[vagrant@devtest ~\]\$'], [endAction])
        lsAction.command = "ls"
        suAction = sshclient.Action("command", ['\[vagrant@devtest ~\]\$'], [lsAction], False)
        suAction.command = "su - vagrant"
        result = ssh.interacts(suAction)
        ssh.close()

    def testPasswordInteract(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = sshclient.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        endAction = sshclient.Action("end", [], [])
        lsAction = sshclient.Action("command", ['\[root@devtest ~\]#'], [endAction])
        lsAction.command = "ls"
        wpAction = sshclient.Action("exception", [], [])
        wpAction.exception = sshclient.AuthenticationFailed()
        passAction = sshclient.Action("command", ['\[root@devtest ~\]#', 'Authentication failure'], [lsAction, wpAction], False)
        passAction.command = "vagrant1"
        suAction = sshclient.Action("command", ['assword:'], [passAction], False)
        suAction.command = "su - "
        result = ssh.interacts(suAction)
        ssh.close()

if __name__ == '__main__':
    unittest.main()
