#!/usr/bin/env python
#encoding: utf-8

import unittest
import nmclient
import StringIO
import xml.dom.minidom

class TestSSHHandler(unittest.TestCase):

    def setUp(self):
        self.outfile = StringIO.StringIO()
        self.host = 'localhost'
        self.userwithpass = 'vagrant'
        self.userwithoutpass = 'root'
        self.userpass = 'vagrant'

    def tearDown(self):
        pass

    def testNoPasswordFSM(self):
        prompt = '\[root@devtest ~\]# '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithoutpass, prompt)
        end_state = fsmexpect.FSMState("end")
        ls_state = fsmexpect.FSMState("command", "ls")
        ls_state.add_next_state('\[vagrant@devtest ~\]\$', end_state)
        su_state = fsmexpect.FSMState("command", "su - vagrant", False)
        su_state.add_next_state('\[vagrant@devtest ~\]\$', ls_state)
        result = su_state.start(ssh.p_expect())
        ssh.close()

    def testPasswordFSM(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        end_state = fsmexpect.FSMState("end")
        ls_state = fsmexpect.FSMState("command", "ls")
        ls_state.add_next_state('\[root@devtest ~\]#', end_state)
        wp_state = fsmexpect.FSMState("exception")
        wp_state.exception = fsmexpect.AuthenticationFailed()
        pass_state = fsmexpect.FSMState("command", "vagrant", False)
        pass_state.add_next_state('\[root@devtest ~\]#', ls_state)
        pass_state.add_next_state('Authentication failure', wp_state)
        su_state = fsmexpect.FSMState("command", "su - ", False)
        su_state.add_next_state('assword:', pass_state)
        result = su_state.start(ssh.p_expect())
        ssh.close()

    def testPasswordChangePrompt(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = fsmexpect.SSHHandler(self.host,  self.userwithpass, prompt, self.userpass)
        ssh.change_prompt('su -', '\[root@devtest ~\]# ', 'vagrant')
        ssh.close()

    def testNoPasswordChangePrompt(self):
        prompt = '\[root@devtest ~\]# '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithoutpass, prompt)
        ssh.change_prompt('su - vagrant', '\[vagrant@devtest ~\]\$ ')
        ssh.close()

    def testNoPasswordLogin(self):
        prompt = '\[root@devtest ~\]# '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithoutpass, prompt)
        result = ssh.run_cmd('ls', self.outfile)
        self.assertEqual(result, self.outfile.getvalue(), "Printout of run_cmd is not equal to return value")
        ssh.close()

    def testPasswordLogin(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        result = ssh.run_cmd('ls', self.outfile)
        self.assertEqual(result, self.outfile.getvalue(), "Printout of run_cmd is not equal to return value")
        ssh.close()

    def testLongOutput(self):
        prompt = '\[root@devtest ~\]# '
        ssh = fsmexpect.SSHHandler(self.host, self.userwithoutpass, prompt)
        result = ssh.run_cmd("more /root/sshexpect/fsmexpect.py", self.outfile)
        self.assertEqual(result, self.outfile.getvalue(), "Printout of run_cmd is not equal to return value")
        ssh.close()

    def testWrongHost(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try:
            fsmexpect.SSHHandler('Nonexisithost', self.userwithpass, prompt, self.userpass)
        except fsmexpect.ConnectionError, e:
            pass

    def testWrongPasswd(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try:
            fsmexpect.SSHHandler(self.host, self.userwithpass, prompt, 'sjla')
        except fsmexpect.AuthenticationFailed, e:
            pass

    def testWrongUser(self):
        prompt = '\[vagrant@devtest ~\]\$ '
        try:
            fsmexpect.SSHHandler(self.host, 'saffa', prompt)
        except fsmexpect.AuthenticationFailed, e:
            pass

    def testWrongPrompt(self):
        prompt = '\[vagrat@dvtest ~\]\$ '
        try:
            fsmexpect.SSHHandler(self.host, self.userwithpass, prompt, self.userpass)
        except fsmexpect.Timeout, e:
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
        scp = fsmexpect.SCPHandler(self.host, self.userwithoutpass)
        scp.upload('./unit.py', '/root/uploadedfile')
        scp.download('/root/uploadedfile', '/root/downloadedfile')

    def testPassword(self):
        scp = fsmexpect.SCPHandler(self.host, self.userwithpass, self.userpass)
        scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        scp.download('/home/vagrant/uploadedfile', '/home/vagrant/downloadedfile')

    def testWrongHost(self):
        scp = fsmexpect.SCPHandler('NonexistHost', self.userwithoutpass)
        try:
            scp.upload('./unit.py', '/root/uploadedfile')
        except fsmexpect.SCPFailed, e:
            pass
        try:
            scp.download('/root/uploadedfile', '/root/downloadedfile')
        except fsmexpect.SCPFailed, e:
            pass

    def testWrongPassword(self):
        scp = fsmexpect.SCPHandler(self.host, self.userwithpass, 'vagra111')
        try:
            scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        except fsmexpect.AuthenticationFailed, e:
            pass

    def testWrongUser(self):
        scp = fsmexpect.SCPHandler(self.host, 'vagrnt')
        try:
            scp.upload('./unit.py', '/home/vagrant/uploadedfile')
        except fsmexpect.AuthenticationFailed, e:
            pass

    def testNoPermission(self):
        scp = fsmexpect.SCPHandler(self.host, self.userwithpass, self.userpass)
        try:
            scp.upload('./unit.py', '/root/uploadedfile')
        except fsmexpect.SCPFailed, e:
            pass

class TestNetConfHandler(unittest.TestCase):

    def setUp(self):
        self.host = 'localhost'
        self.user = 'root'
        self.userpass = 'passw0rd'
        self.port = 8300

    def tearDown(self):
        pass

    def testConnect(self):
        netconf = fsmexpect.NetconfSSHHandler()
        netconf.connect(self.host, self.user, self.userpass, 10, self.port)
        netconf.close()
        netconf = fsmexpect.NetconfSSHHandler()
        netconf.connect(self.host, self.user, self.userpass, 10, self.port)
        netconf.close()

    def testSyncRequest(self):
        netconf = fsmexpect.NetconfSSHHandler()
        netconf.connect(self.host, self.user, self.userpass, 10, self.port)
        doc = xml.dom.minidom.Document()
        nschemas = fsmexpect.xmlnode(doc, 'ncm:schemas')
        nnetconf_state = fsmexpect.xmlnode(doc, 'ncm:netconf-state', {'xmlns:ncm':'urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring'}, [nschemas])
        nfilter = fsmexpect.xmlnode(doc, 'filter', {'type': 'subtree'}, [nnetconf_state])
        nget = fsmexpect.xmlnode(doc, 'get', {}, [nfilter])
        print netconf.sync_request(nget)
        netconf.close()


if __name__ == '__main__':
    unittest.main()
