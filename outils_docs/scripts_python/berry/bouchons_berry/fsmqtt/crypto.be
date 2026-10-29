# Bouchon de crypto.MD5 pour banc_fsmqtt.be (berry.exe n'a pas crypto) : empreinte NON cryptographique (somme et
# longueur), meme interface update()/finish() -> bytes. Le banc calcule l'attendu avec ce meme bouchon.
var crypto = module("crypto")
class MD5
    var a, b, n
    def init() self.a = 1 self.b = 0 self.n = 0 end
    def update(d)
        for i: 0 .. size(d) - 1    self.a = (self.a + d[i]) % 65521  self.b = (self.b + self.a) % 65521    end
        self.n += size(d)
    end
    def finish() var r = bytes() r.add(self.b, -2) r.add(self.a, -2) r.add(self.n, -4) return r end
end
crypto.MD5 = MD5
return crypto
