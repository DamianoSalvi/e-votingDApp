from pyteal import *
from pyteal.ast.bytes import Bytes
from pyteal_helpers import program


def approval():
    #locals
    local_registered = Bytes("registered") # int
    #globals
    global_owner = Bytes("owner")  # byteslice
    global_regBegin = Bytes("regBegin") # int
    global_regEnd = Bytes("regEnd") # int
    global_voteBegin =Bytes("voteBegin") # int
    global_voteEnd = Bytes("voteEnd") # int
    global_votesA = Bytes("votesA") # int
    global_votesB = Bytes("votesB") # int
    global_tokenID = Bytes("tokenID") # int id del token di voto cosi non è hardcoded

    #ops
    op_vote = Bytes("vote")

    #candidati
    a = Bytes("a")
    b = Bytes("b")

    #scratchvars
    scratch_counter = ScratchVar(TealType.uint64)

    def increment(a: Int):
        return Seq(
            Cond(
            [a==Int(1),Seq(scratch_counter.store(App.globalGet(global_votesA)),
                            App.globalPut(global_votesA, scratch_counter.load()
                            +Int(1)))],
            [a==Int(2),Seq(scratch_counter.store(App.globalGet(global_votesB)),
                            App.globalPut(global_votesB, scratch_counter.load()
                            +Int(1)))],
            ),
    )

    @Subroutine(TealType.none)
    def vote():
        return Seq(
            # basic sanity checks
            program.check_self(
                group_size=Int(2),
                group_index=Int(0),
            ),
            Assert(
                And(
                    #controllo finestra temporale per il voto
                    Global.round() >= App.globalGet(global_voteBegin),
                    Global.round() <= App.globalGet(global_voteEnd),
                    #controllo se chi sta cercando di votare è registrato
                    App.localGet(Txn.sender(),local_registered) == Int(1),
                    
                    #il gruppo di transazioni deve essere di 2 (voto e transfer)
                    #Global.group_size() == Int(2),
                    #la seconda transazione deve essere un transfer di un asset
                    Gtxn[1].type_enum() == TxnType.AssetTransfer,
                    #il destinatario dell'asset deve essere l'autorità centrale che ha deployato il contratto
                    Gtxn[1].asset_receiver() == App.globalGet(global_owner),
                    #l'asset trasferito deve essere il token di voto (hardcored al momento)
                    Gtxn[1].xfer_asset() == App.globalGet(global_tokenID),
                    #uno e un solo token deve essere trasferito
                    Gtxn[1].asset_amount() == Int(1),

                    #deve essere presente un secondo argomento per la preferenza
                    Txn.application_args.length() == Int(2),
                )
            ),
            #a seconda del secondo argomento viene chiamata la funzione di increment con due argomenti diversi
            Cond( 
            [Txn.application_args[1] == a, increment(Int(1))],
            [Txn.application_args[1] == b, increment(Int(2))],
            ),
            Approve(),
        )

    
    return program.event(
        init=Seq(
            [  
                Assert(Txn.application_args.length() == Int(5)),
                App.globalPut(global_owner, Txn.sender()),
                App.globalPut(global_regBegin, Btoi(Txn.application_args[0])),
                App.globalPut(global_regEnd, Btoi(Txn.application_args[1])),
                App.globalPut(global_voteBegin, Btoi(Txn.application_args[2])),
                App.globalPut(global_voteEnd, Btoi(Txn.application_args[3])),
                App.globalPut(global_tokenID,Btoi(Txn.application_args[4])),
                Approve(),
            ]
        ),
        opt_in=Seq(
            Assert(
                And(
                    Global.round() >= App.globalGet(global_regBegin),
                    Global.round() <= App.globalGet(global_regEnd),
                )
            ),
            App.localPut(Txn.sender(),Bytes("registered"), Int(1)),
            Approve(),
    ),
        no_op=Seq(
            Cond(
                [
                    Txn.application_args[0] == op_vote,
                    vote(),
                ],
            ),
            Reject(),
        ),
    )


def clear():
    return Approve()
