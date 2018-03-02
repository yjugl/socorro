# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from crontabber.base import BaseCronApp
from crontabber.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class _MatViewBase(BaseCronApp):

    app_version = '1.0'  # default
    app_description = "Run certain matview stored procedures"

    def get_proc_name(self):
        return self.proc_name

    def run_proc(self, connection, signature=None):
        cursor = connection.cursor()
        if signature:
            cursor.callproc(self.get_proc_name(), signature)
            _calling = '%s(%r)' % (self.get_proc_name(), signature)
        else:
            cursor.callproc(self.get_proc_name())
            _calling = '%s()' % (self.get_proc_name(),)
        self.config.logger.info(
            'Result from calling %s: %r' %
            (_calling, cursor.fetchone())
        )
        if connection.notices:
            self.config.logger.info(
                'Notices from calling %s: %s' %
                (_calling, connection.notices)
            )

    def run(self, connection):
        self.run_proc(connection)


@as_backfill_cron_app
class _MatViewBackfillBase(_MatViewBase):

    def run(self, connection, date):
        target_date = (date - datetime.timedelta(days=1)).date()
        self.run_proc(connection, [target_date])


class ProductVersionsCronApp(_MatViewBase):
    """Runs update_product_versions stored procedure

    Updates product_versions and product_versions_builds tables from
    releases_raw table.

    """
    proc_name = 'update_product_versions'
    app_name = 'product-versions-matview'
    depends_on = (
        'reports-clean',
    )


class SignaturesCronApp(_MatViewBackfillBase):
    """Runs update_signatures stored procedure

    Updates signatures, signatures_products, and signature_products_rollup
    tables from reports table data.

    """
    proc_name = 'update_signatures'
    app_name = 'signatures-matview'
    depends_on = ('reports-clean',)


class ADUCronApp(_MatViewBackfillBase):
    """Runs update_adu stored procedure

    Updates product_adu table from raw_adi.

    """
    proc_name = 'update_adu'
    app_name = 'adu-matview'
    depends_on = ('fetch-adi-from-hive', 'reports-clean',)


class BuildADUCronApp(_MatViewBackfillBase):
    """Runs update_build_adu stored procedure

    Updates build_adu table using data from raw_adi.

    """
    proc_name = 'update_build_adu'
    app_name = 'build-adu-matview'
    depends_on = ('fetch-adi-from-hive', 'reports-clean')


class ReportsCleanCronApp(_MatViewBackfillBase):
    """Runs update_reports_clean stored procedure

    Updates reports_bad, reports_clean, reports_user_info, signatures, and
    other tables from reports table.

    """
    proc_name = 'update_reports_clean'
    app_name = 'reports-clean'
    app_version = '1.0'
    app_description = ""

    def run(self, connection, date):
        date -= datetime.timedelta(hours=2)
        self.run_proc(connection, [date])


class GraphicsDeviceCronApp(_MatViewBackfillBase):
    """Runs update_graphics_devices stored procedure

    Updates graphics_device table with new data from raw_crashes table.

    """
    proc_name = 'update_graphics_devices'
    app_name = 'graphics-device-matview'
