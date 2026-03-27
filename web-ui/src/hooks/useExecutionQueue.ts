import { useEffect, useState } from "react";
import { normalizePackageQueue, normalizePackageValue } from "../lib/appHelpers";
import type { TestPackageOption } from "../types/app";

type MessageApi = {
  info: (content: string) => void;
};

type UseExecutionQueueOptions = {
  packages: TestPackageOption[];
  selectedPackage?: string;
  msgApi: MessageApi;
};

function isAllCasesValue(value: string): boolean {
  return !value.endsWith(".py");
}

function useExecutionQueue({ packages, selectedPackage, msgApi }: UseExecutionQueueOptions) {
  const [suite, setSuite] = useState("all");
  const [executionPackages, setExecutionPackages] = useState<string[]>([]);
  const [selectedExecutionIndex, setSelectedExecutionIndex] = useState<number>(-1);

  useEffect(() => {
    const values = packages.map((item) => item.value);
    setExecutionPackages((old) => {
      const filtered = normalizePackageQueue(old).filter((p) => values.includes(p));
      return filtered.length ? filtered : values[0] ? [values[0]] : [];
    });
    setSelectedExecutionIndex((old) => {
      if (!values.length) return -1;
      if (old < 0) return 0;
      return Math.min(old, values.length - 1);
    });
  }, [packages]);

  const addSelectedCase = () => {
    const selectedValue = normalizePackageValue(selectedPackage);
    if (!selectedValue) return;

    const selectedIsAll = isAllCasesValue(selectedValue);
    const hasAllInQueue = executionPackages.some(isAllCasesValue);

    if (executionPackages.includes(selectedValue)) {
      msgApi.info("该用例已在待执行列表中");
      setSelectedExecutionIndex(executionPackages.indexOf(selectedValue));
      return;
    }

    if (selectedIsAll) {
      setExecutionPackages([selectedValue]);
      setSelectedExecutionIndex(0);
      msgApi.info("已选择“全部用例”，将不再添加单独用例");
      return;
    }

    if (hasAllInQueue) {
      msgApi.info("当前已选择“全部用例”，请先移除后再添加单独用例");
      return;
    }

    const next = normalizePackageQueue([...executionPackages, selectedValue]);
    setExecutionPackages(next);
    setSelectedExecutionIndex(next.length - 1);
  };

  const addAllCases = () => {
    if (executionPackages.some(isAllCasesValue)) {
      msgApi.info("当前已选择“全部用例”，不能再批量添加单独用例");
      return;
    }

    let added = 0;
    let skipped = 0;
    const next = normalizePackageQueue(executionPackages);
    for (const p of packages) {
      if (isAllCasesValue(p.value)) {
        continue;
      }
      if (next.includes(p.value)) {
        skipped += 1;
      } else {
        next.push(p.value);
        added += 1;
      }
    }
    setExecutionPackages(next);
    if (next.length) setSelectedExecutionIndex(next.length - 1);
    msgApi.info(`批量添加完成：新增 ${added}，跳过重复 ${skipped}`);
  };

  const removeSelectedCase = () => {
    if (selectedExecutionIndex < 0 || selectedExecutionIndex >= executionPackages.length) return;
    const next = executionPackages.filter((_, idx) => idx !== selectedExecutionIndex);
    setExecutionPackages(normalizePackageQueue(next));
    setSelectedExecutionIndex(Math.min(selectedExecutionIndex, next.length - 1));
  };

  const moveSelectedCase = (offset: number) => {
    const from = selectedExecutionIndex;
    const to = from + offset;
    if (from < 0 || from >= executionPackages.length) return;
    if (to < 0 || to >= executionPackages.length) return;
    const next = normalizePackageQueue(executionPackages);
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setExecutionPackages(normalizePackageQueue(next));
    setSelectedExecutionIndex(to);
  };

  const clearExecutionPackages = () => {
    setExecutionPackages([]);
    setSelectedExecutionIndex(-1);
  };

  return {
    suite,
    executionPackages,
    selectedExecutionIndex,
    setSuite,
    setSelectedExecutionIndex,
    addSelectedCase,
    addAllCases,
    removeSelectedCase,
    moveSelectedCase,
    clearExecutionPackages,
  };
}

export default useExecutionQueue;
