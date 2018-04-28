#!/usr/bin/env python
#encoding: utf-8

import unittest
import sshclient
import sys
import StringIO

class TestSSHHandler(unittest.TestCase):

    def setUp(self):
        self.outfile = StringIO.StringIO()
        self.host = 'localhost'
        self.userwithpass = 'vagrant'
        self.userwithoutpass = 'root'
        self.userpass = 'vagrant'

    def tearDown(self):
        pass

    def testNoPasswordLogin(self):
        prompt = '\[root@devtest ~\]# '
        ssh = sshclient.SSHHandler(self.host, self.userwithoutpass, prompt)
        result = ssh.runCommand('ls', self.outfile)
        self.assertEqual(result, self.outfile.getvalue(), "Printout of runCommand is not equal to return value")
        ssh.close()

    def testPasswordLogin(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = sshclient.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        result = ssh.runCommand('ls', self.outfile)
        self.assertEqual(result, self.outfile.getvalue(), "Printout of runCommand is not equal to return value")
        ssh.close()

    def testWrongHost(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try: 
            sshclient.SSHHandler('Nonexisithost', self.userwithpass, prompt, self.userpass)
        except sshclient.ConnectionError, e:
            pass

    def testWrongPasswd(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try:
            sshclient.SSHHandler(self.host, self.userwithpass, prompt, 'sjla')
        except sshclient.AuthenticationFailed, e:
            pass

    def testWrongUser(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try:
            sshclient.SSHHandler(self.host, 'saffa', prompt)
        except sshclient.AuthenticationFailed, e:
            pass

    def testWrongPrompt(self):
        prompt = '\[vagrat@dvtest ~\]\$ '
        try:
            sshclient.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        except sshclient.Timeout, e:
            pass

class TestSCPHandler(unittest.TestCase):

    def setUp(self):
        self.host = 'localhost'
        self.userwithpass = 'vagrant'
        self.userwithoutpass = 'root'
        self.userpass = 'vagrant'

    def tearDown(self):
        pass

    def testNoPassword(self):
        scp = sshclient.SCPHandler(self.host, self.userwithoutpass)
        scp.upload('./unit.py', '/root/uploadedfile')
        scp.download('/root/uploadedfile', '/root/downloadedfile')

    def testPassword(self):
        scp = sshclient.SCPHandler(self.host, self.userwithpass, self.userpass)
        scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        scp.download('/home/vagrant/uploadedfile', '/home/vagrant/downloadedfile')

    def testWrongHost(self):
        scp = sshclient.SCPHandler('NonexistHost', self.userwithoutpass)
        try:
            scp.upload('./unit.py', '/root/uploadedfile')
        except sshclient.SCPFailed, e:
            pass
        try:
            scp.download('/root/uploadedfile', '/root/downloadedfile')
        except sshclient.SCPFailed, e:
            pass

    def testWrongPassword(self):
        scp = sshclient.SCPHandler(self.host, self.userwithpass, 'vagra111')
        try:
            scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        except sshclient.AuthenticationFailed, e:
            pass 

    def testWrongUser(self):
        scp = sshclient.SCPHandler(self.host, 'vagrnt')
        try:
            scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        except sshclient.AuthenticationFailed, e:
            pass

    def testNoPermission(self):
        scp = sshclient.SCPHandler(self.host, self.userwithpass, self.userpass)
        try:
            scp.upload('./unit.py', '/root/uploadedfile')
        except sshclient.SCPFailed, e:
            pass

if __name__ == '__main__':
    unittest.main()

