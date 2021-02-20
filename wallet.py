class Transaction:
    def __init__(self, *args):
        self.sum, self.origin = args
        self.__other = None

    def pay(self, other):
        if (self.__other is not None) and (self.__other is not other):
            raise Exception("Wrong account")
        if (self.origin.balance>=self.sum):
            self.origin.balance -= self.sum
            other.balance += self.sum
            self.__other = other
        else:
            raise Exception("Transaction failed")

    def revert(self):
        self.__other.withdraw(self.sum).pay(self.origin)

    def pay_again(self):
        self.pay(self.__other)


class Wallet:
    def __init__(self, balance):
        self.balance = balance

    def withdraw(self, sum):
        return Transaction(sum, self)

    def topup(self, src):
        src.pay(self)

    def __repr__(self):
        return str(self.balance)


class InfiniteWallet(Wallet):
    def __init__(self):
        self.balance=0

    def withdraw(self, sum):
        self.balance=sum
        return super().withdraw(sum)

class FakeStockInfo:
    def __init__(self):
        self.prices = dict(aapl=500, ehth=300)

    def __getitem__(self, ticker):
        return self.prices[ticker]

class Position:
    def __init__(self, ticker, amount):
        self.ticker = ticker
        self.amount = amount




# Testing area
misha = Wallet(500)
yulia = Wallet(1000)

def printboth():
    print(f"m: {misha}\ny: {yulia}\n")

misha.topup(yulia.withdraw(50))
printboth()
formetro = yulia.withdraw(42)
formetro.pay(misha)
printboth()
formetro.pay_again()
printboth()
formetro.revert()
printboth()


parents = InfiniteWallet()

misha.topup(parents.withdraw(5000))
printboth()
misha.topup(parents.withdraw(5000))
printboth()
misha.topup(parents.withdraw(5000))
printboth()










