# fsmexpect

**The project fsmexpect is deprecated and was rename to nmclient. More access ways are provided in nmclient, indludes SSH, SCP, Netconf. Module fsmstate is still here to provide the execution flow of ssh command to user.**

This project provides an FSM model base on pexcept to run ssh commands on remote host.

"FSMState" is the core unit of the FSM model. Now there are 4 types of them supported:
- command, which will send command to remote host, followed by '\n'.
- operate, which will send a character to remote host.
- end, which is an indicator of success.
- exception, which will raise a pre-define exception.

Each object of FSMState is a "state" of FSM. The state will transfer by command and its output from remote host.
Following is an example of running privilege command.

![fsm.jpg](http://o7gg8x7fi.bkt.clouddn.com/fsm.jpg)

**State 1.** This state will send command to remote host, when its expect string found in output, it will transfer to
  - State 2, if remote host indicates an password needed
  - State 3, if remote host indicates the output is long and more page is coming.
  - State 4, if remote host indicates a shell prompt.

**State 2.** This state will send password to remote host, and will transfer to
  - State 3, if the password is correct and remote host indicates the output is long and more page is coming.
  - State 4, if the password is correct and remote host indicates a shell prompt.
  - State 5, if the password is wrong.

**State 3.** This state will send a character (generally it is "ANY key") to indicate remote host to print next page, and will transfer to
  - State 3 it self, if there are still more page left.
  - State 4, if all page has been printed and remote host indicates a shell prompt.

**State 4.** This state represents an successful FSM procedure.

**State 5.** This state represents an failed FSM procedure and the reason can be included in the exception raised.

Following is the code to represent this FSM:

``` python
cmd_state = fsmexpect.FSMState("command", command)
succ_state = fsmexpect.FSMState("end")
pass_state = fsmexpect.FSMState("command", password)
failed_state = fsmexpect.FSMState("exception", AuthenticationFailed())
continue_state = fsmexpect.FSMState("operate", " ")
cmd_state.add_next_state(shell_prompt,  succ_state)                # Success directly
cmd_state.add_next_state('.+assword:', pass_state)                 # Need password
cmd_state.add_next_state('--More--\(\d+%\)', continue_state)       # Long output
pass_state.add_next_state(shell_prompt, succ_state)                # Success directly
pass_state.add_next_state("Authentication failure", failed_state)  # Wrong password
pass_state.add_next_state('--More--\(\d+%\)', continue_state)      # Long output
continue_state.add_next_state(shell_prompt, succ_state)
continue_state.add_next_state('--More--\(\d+%\)', continue_state)
```
