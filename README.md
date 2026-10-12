# lab2
## Схема
Windows host -> Ubuntu (VMware Workstation) -> Ubuntu (KVM) -> Docker Compose -> Backend & Frontend containers
## Запуск
- Поставить ip VM в `inventory.ini` (в моем случае `192.168.122.108`);
- Убедиться что VM запущена и публичный ssh ключ отправлен (проверка: `virsh list | grep people-app-vm`, запуск: `virsh start people-app-vm`);
- Запустить `cd ./lab2/ansible && ansible-playbook site.yml`
- Открыть страницу на `http://<IP>:8080` (`http://192.168.122.108:8080`)
