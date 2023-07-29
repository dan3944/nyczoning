import download
import unittest
from dataclasses import dataclass


@dataclass
class ReadTableTestCase:
    pdf_name: str
    want_num_commission_votes: int
    want_num_public_hearings: int


class TestParsePdf(unittest.TestCase):
    def test_num_rows(self):
        test_cases = [
            ReadTableTestCase(
                pdf_name='pdfs/2023-07-12 100000.pdf',
                want_num_commission_votes=9,
                want_num_public_hearings=7),
            ReadTableTestCase(
                pdf_name='pdfs/2023-07-24 130000.pdf',
                want_num_commission_votes=1,
                want_num_public_hearings=0),
            ReadTableTestCase(
                pdf_name='pdfs/2023-07-26 100000.pdf',
                want_num_commission_votes=6,
                want_num_public_hearings=1),
            ReadTableTestCase(
                pdf_name='pdfs/2023-08-09 100000.pdf',
                want_num_commission_votes=8,
                want_num_public_hearings=4),
        ]

        for i, test in enumerate(test_cases):
            print(f'Test {i + 1}: {test.pdf_name}')
            with open(test.pdf_name, 'rb') as f:
                pdf_bytes = f.read()

            got_commission_votes = download.read_table(pdf_bytes, 'commission votes today on:', 'public hearings today on:')
            got_public_hearings = download.read_table(pdf_bytes, 'public hearings today on:')
            self.assertEqual(len(got_commission_votes), test.want_num_commission_votes)
            self.assertEqual(len(got_public_hearings), test.want_num_public_hearings)


if __name__ == '__main__':
    unittest.main()
