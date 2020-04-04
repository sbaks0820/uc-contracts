import dump
import gevent
from itm import ITM, UCWrapper
from collections import defaultdict

class Syn_FWrapper(UCWrapper):
    def __init__(self, channels):
        self.curr_round = 1
        self.delay = 0
        self.todo = { self.curr_round: [] }
        # TODO keep the round here until something happens
        # alternate theory: the round won't change unless something exists todo
        # in future rounds
        #self.adv_callme(self.curr_round)
        UCWrapper.__init__(self, 'wrap', 'me', channels)

    def fschedule(self, sender, f, args, delta):
        print('\033[1mFschedule\033[0m', sender, delta)
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (f,args) )
        self.delay += 1
        print('new delay', self.delay)
        self.w2f.write( (sender, ('OK',)) )

    def pschedule(self, sender, f, args, delta):
        print('\033[1mPschedule\033[0m', sender, delta)
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (f,args) )
        self.delay += 1
        print('new delay', self.delay)
        self.w2p.write( (sender, ('OK',)) )

    def adv_delay(self, t):
        self.delay += t
        dump.dump()

    def adv_execute(self, r, i):
        print('Execing a codeblock')
        f,args = self.todo[r].pop(i)
        f(*args)

    def next_round(self):
        rounds = self.todo.keys()
        for r in sorted(rounds):
            if r >= self.curr_round and len(self.todo[r])>0:
                return r
        raise self.curr_round

    def poll(self):
        if self.delay > 0:
            self.delay -= 1
            print('delay', self.delay)
            print('writing to w2a')
            self.w2a.write( ('poll',) )
        else:
            self.curr_round = self.next_round()
            print('New round', self.curr_round)
            r = self.curr_round
            if len(self.todo[r]): self.adv_execute(r, 0)
            else: dump.dump()

    def clock_round(self, sender, channel):
        channel.write( (sender, ('round',self.curr_round)) )

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'poll':
            self.poll()
        else:
            dump.dump()

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.fschedule(sender, msg[1], msg[2], msg[3])
        else:
            dump.dump()

    # TODO revisit this to see if adversary can delay callme actions
    def party_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        self.todo[r].append( (lambda: self.w2a.write(('shotout',)), ()) )
        self.w2p.write( ('OK',) )

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.pschedule(msg[1], msg[2], msg[3])
        elif msg[0] == 'clock-round':
            self.clock_round(sender, self.w2p)
        elif msg[0] == 'callme':
            self.party_callme(sender)
        else:
            dump.dump()

    def adv_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        self.todo[r].append( (lambda: self.w2a.write(('shoutout',)), ()) )
        self.w2a.write( ('OK',) )

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        print('msg', msg)
        if msg[0] == 'delay':
            self.adv_delay(msg[1])
        elif msg[0] == 'exec':
            self.adv_execute(msg[1], msg[2])
        elif msg[0] == 'callme':
            self.adv_callme(msg[1])
        else:
            dump.dump()

