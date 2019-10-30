# Copyright 2018 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    # Add temporary type column
    cr.execute('ALTER TABLE fsm_order ADD temporary_type VARCHAR(20)')
    # Store pre-migration type
    cr.execute('UPDATE fsm_order SET temporary_type = type')
