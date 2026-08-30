<template>
  <div class="page-container">
    <h2>📅 每日签到</h2>
    <div class="sign-card">
      <p>今日签到状态：<span style="color: #ff9900; font-weight: bold;">未签到</span></p>
      <button class="sign-btn">点击签到</button>
    </div>
  </div>
</template>

<style scoped>
.sign-card {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  margin-top: 15px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
  color: #606266;
}
.sign-btn {
  margin-top: 20px;
  padding: 10px 30px;
  background: #ff9900;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}
.sign-btn:hover { background: #e68a00; }
</style>