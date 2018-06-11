#!/usr/bin/python
#coding=utf8

import sys
import pexpect
import fsmstate
import common

class SCPHandler:

    def __init__(self, ip, loginUser, loginPass='', port=22):
        self.ip = ip
        self.loginUser = loginUser
        self.loginPass = loginPass
        self.port = port

    def need_pass(self, scp, timeout=10):
        try:
            scp.expect(['.+assword:'], timeout)
            return True, None
        except pexpect.EOF:
            common.debug("SCP exit with %s" % (scp.exitstatus))
            return False, scp.exitstatus

    def upload(self, localFile, remoteFile, timeout=10):
        scp_cmd = 'scp -o StrictHostKeyChecking=no -P %d %s %s@%s:%s' % (self.port, localFile, self.loginUser, self.ip, remoteFile)
        common.debug("Start SCP upload: %s" % (scp_cmd))
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp, timeout)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp, timeout)
        if need_pass:
            raise common.AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise common.SCPFailed("Upload failed. Exit code: %s" %(exitstatus))


    def download(self, remoteFile, localFile, timeout=10):
        scp_cmd = 'scp -o StrictHostKeyChecking=no -P %d %s@%s:%s %s' % (self.port, self.loginUser, self.ip, remoteFile, localFile)
        common.debug("Start SCP download: %s" % (scp_cmd))
        scp = pexpect.spawn(scp_cmd)
        need_pass, exitstatus = self.need_pass(scp, timeout)
        if need_pass:
            scp.sendline(self.loginPass)
            need_pass, exitstatus = self.need_pass(scp, timeout)
        if need_pass:
            raise common.AuthenticationFailed("Authentication failed.")
        else:
            if exitstatus:
                raise common.SCPFailed("Upload failed. Exit code: %s" %(exitstatus))

class SSHHandler:

    def __init__(self, ip, loginUser, prompt, loginPass='', timeout=10, port=22):
        ssh_cmd = 'ssh -o StrictHostKeyChecking=no -p %d %s@%s' % (port, loginUser, ip)
        common.debug("Start ssh: %s" % (ssh_cmd))
        self.ssh = pexpect.spawn(ssh_cmd)
        try:
            i = self.ssh.expect([prompt, '.+assword:'], timeout)
            if i == 0:
                self.prompt = prompt
                self.user = loginUser
                return
        except pexpect.EOF:
            self.ssh.close()
            raise common.ConnectionError()
        except pexpect.TIMEOUT:
            self.ssh.close()
            raise common.Timeout("SSH connection timeout!")

        pass_state = fsmstate.FSMState("command", loginPass, False)
        def callback():
            self.prompt = prompt
            self.user = loginUser
        succ_state = fsmstate.FSMState("end", callback)
        fail_state = fsmstate.FSMState("exception", common.AuthenticationFailed())
        pass_state.add_next_state('.+assword: ', fail_state)
        pass_state.add_next_state(prompt, succ_state)
        pass_state.start(self.ssh)

    def p_expect(self):
        return self.ssh

    def change_prompt(self, cmd, prompt, password='', timeout=10):
        common.debug("Run %s and change prompt to %s" % (cmd, prompt))
        cmd_state = fsmstate.FSMState("command", cmd)
        def callback():
            self.prompt = prompt
        succ_state = fsmstate.FSMState("end", callback)
        pass_state = fsmstate.FSMState("command", password)
        fail_state = fsmstate.FSMState("exception", common.AuthenticationFailed())

        cmd_state.add_next_state('.+assword:', pass_state)                 # Need password
        cmd_state.add_next_state(prompt, succ_state)                       # Success directly
        pass_state.add_next_state(prompt, succ_state)                      # Success
        pass_state.add_next_state("Authentication failure", fail_state)    # Wrong password
        cmd_state.start(self.ssh, timeout)

    def run_cmd(self, cmd, out=sys.stdout, password='', timeout=10):
        common.debug("Run %s" % (cmd))
        cmd_state = fsmstate.FSMState("command", cmd)
        succ_state= fsmstate.FSMState("end")
        pass_state = fsmstate.FSMState("command", password)
        fail_state = fsmstate.FSMState("exception", common.AuthenticationFailed())
        continue_state = fsmstate.FSMState("operate", " ")

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
        common.debug("Close ssh.")
        self.ssh.close()

import xml.dom.minidom
import threading
import traceback
import time

def xmlnode(doc, tag, attributes={}, children=[]):
    node = doc.createElement(tag)
    for k, v in attributes.items():
        node.setAttribute(k, v)
    for child in children:
        node.appendChild(child)
    return node

class NetconfSSHHandler:

    def __init__(self, capabilities=[]):
        self.request_queue = []
        self.capabilities = ['urn:ietf:params:netconf:base:1.0']
        self.capabilities += capabilities
        self.remote_capabilities = []
        self.ssh = None
        self.sessionid = None
        self.replies = {}
        self.next_messageid = 1

    def start_listening_printout(self):
        thread = threading.Thread(target=self.process_printout, args=())
        thread.setDaemon(True)
        thread.start()

    def process_printout(self):
        while True:
            common.debug('Waiting printout...')
            try:
                self.ssh.expect(']]>]]>')
                printout = self.ssh.before.strip()
                # common.debug("Receive printout:\n" + printout)
                doc = xml.dom.minidom.parseString(printout)
                if doc.documentElement.tagName == 'rpc-reply':
                    messageid = doc.documentElement.getAttribute('message-id')
                    common.debug("Get reply of message %s." %(messageid))
                    if not self.replies.has_key(messageid):
                        # SYNC request, put the reply into self.replies.
                        self.replies[messageid] = doc.documentElement
                    else:
                        # ASYNC request, call the callback in self.replies.
                        self.replies[messageid](doc.documentElement)
            except pexpect.EOF:
                common.debug('Exit printout listening thread.')
                break

    def connect(self, ip, username, passwd='', timeout=10, port=830, subsystem='netconf'):
        ssh_cmd = 'ssh -s -o StrictHostKeyChecking=no -p %d %s@%s %s' % (port, username, ip, subsystem)
        common.debug("Start netconf session: %s" % (ssh_cmd))
        self.ssh = pexpect.spawn(ssh_cmd)
        try:
            i = self.ssh.expect([']]>]]>', '.+assword:'], timeout)
            if i == 1:
                self.ssh.sendline(passwd)
                self.ssh.expect([']]>]]>'], timeout)
            self.parse_remote_capabilities(self.ssh.before)
            common.debug("Start session " + self.sessionid)
            self.start_listening_printout()
            self.send_hello()
            return
        except pexpect.EOF:
            self.ssh.close()
            raise common.ConnectionError()
        except pexpect.TIMEOUT:
            self.ssh.close()
            raise common.Timeout("SSH connection timeout!")

    def parse_remote_capabilities(self, text):
        doc = xml.dom.minidom.parseString(text[text.index('<?xml'):])
        capabilities = doc.getElementsByTagName("capability")
        self.remote_capabilities = []
        for capability in capabilities:
           if capability.childNodes[0].nodeType == capability.TEXT_NODE:
                self.remote_capabilities.append(capability.childNodes[0].data)
        self.sessionid = doc.getElementsByTagName("session-id")[0].childNodes[0].data

    def send_hello(self):
        doc = xml.dom.minidom.Document()
        nhello = doc.createElement('hello')
        doc.appendChild(nhello)
        nhello.setAttribute('xmlns', 'urn:ietf:params:xml:ns:netconf:base:1.0')
        ncapabilities = doc.createElement('capabilities')
        nhello.appendChild(ncapabilities)
        for capability in self.capabilities:
            ncapability = doc.createElement('capability')
            ncapabilities.appendChild(ncapability)
            text = doc.createTextNode(capability)
            ncapability.appendChild(text)
        common.debug("Send hello message. \n" + doc.toxml())
        doc.writexml(self.ssh, encoding="utf-8")
        self.ssh.sendline(']]>]]>')

    def close(self):
        doc = xml.dom.minidom.Document()
        nclose = xmlnode(doc, 'close-session')
        self.sync_request(nclose)
        common.debug("Close netconf session %s." %(self.sessionid))

    def sync_request(self, request, xmlns='urn:ietf:params:xml:ns:netconf:base:1.0'):
        messageid = str(self.next_messageid)
        self.next_messageid += 1
        doc = xml.dom.minidom.Document()
        nrpc = xmlnode(doc, 'rpc', {'xmlns': xmlns, 'message-id': messageid}, [request])
        doc.appendChild(nrpc)
        doc.writexml(self.ssh, encoding="utf-8")
        common.debug("Send sync request message. \n" + doc.toxml())
        self.ssh.sendline(']]>]]>')
        while not self.replies.has_key(messageid):
            pass
        reply = self.replies[messageid]
        del self.replies[messageid]
        return reply

    def async_request(self, request, reply_callback, xmlns='urn:ietf:params:xml:ns:netconf:base:1.0'):
        messageid = str(self.next_messageid)
        self.next_messageid += 1
        self.replies[messageid] = reply_callback
        doc = xml.dom.minidom.Document()
        nrpc = xmlnode(doc, 'rpc', {'xmlns': xmlns, 'message-id': messageid}, [request])
        doc.appendChild(nrpc)
        doc.writexml(self.ssh, encoding="utf-8")
        common.debug("Send sync request message. \n" + doc.toxml())
        self.ssh.sendline(']]>]]>')
