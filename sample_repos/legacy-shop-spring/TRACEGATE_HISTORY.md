# Simulated Process History

## Auth

曾尝试删除 legacyToken，导致 LoginCompatibilityTest 失败。旧版移动端仍依赖 legacyToken。

## Order

曾尝试合并 orderStatus 和 refundStatus，导致退款对账逻辑错误。

## User

曾把 deleteUser 改成 repository.deleteById，导致审计记录断链。

## Payment

曾把签名金额统一为 amountInYuan，导致第三方支付回调签名校验失败。

## Job

曾删除 syncBatchId 幂等检查，账单重跑后重复入账。
