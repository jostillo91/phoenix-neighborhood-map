import unittest
from scoring import clean, ratio, normalize, calculate, WEIGHTS

class ScoringTests(unittest.TestCase):
    def test_sentinels(self):
        for v in [None,'-666666666','nan','inf','-','N','(X)','250,000+']:
            self.assertIsNone(clean(v))
        self.assertEqual(clean('0'),0)
    def test_ratios(self):
        self.assertIsNone(ratio(0,0))
        self.assertIsNone(ratio(11,10))
        self.assertEqual(ratio(25,100),25)
    def test_normalization(self):
        for reverse in [False,True]:
            self.assertEqual(normalize(50,[10,50,90],reverse),50)
            self.assertEqual(normalize(-100,[10,50,90],reverse),100 if reverse else 0)
            self.assertEqual(normalize(1000,[10,50,90],reverse),0 if reverse else 100)
        self.assertEqual(normalize(0,[0,0,50],True),50)
    def test_missing_weight_gate(self):
        rows=[{'raw_'+k:v for k in WEIGHTS} for v in range(10,100,10)]
        rows[0]['raw_value']=None
        rows[1]['raw_value']=None;rows[1]['raw_affordability']=None
        rows[2]['raw_income']=None
        calculate(rows)
        self.assertEqual(rows[0]['coverage'],85)
        self.assertIsNotNone(rows[0]['overall'])
        self.assertIsNone(rows[1]['overall'])
        self.assertIsNone(rows[2]['overall'])
        for r in rows:
            for k in [*WEIGHTS,'overall']:
                if r[k] is not None:self.assertTrue(0<=r[k]<=100)
if __name__=='__main__':unittest.main()
